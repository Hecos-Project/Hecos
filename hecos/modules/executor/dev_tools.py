"""
hecos/modules/executor/dev_tools.py
Project navigation, code search, syntax verification, and real project test runner
for Hecos EXECUTOR (separate from the isolated AST jail in sandbox.py).
"""

import ast
import fnmatch
import json
import os
import py_compile
import shlex
import shutil
import subprocess
import sys
from typing import Optional

from .file_manager import AgentTracer, _is_safe_path, logger

_IGNORED_DIRS = {
    ".git",
    "__pycache__",
    "python_env",
    "venv",
    ".venv",
    "node_modules",
    ".pytest_cache",
    ".mypy_cache",
    "dist",
    "build",
    ".eggs",
}


def _find_hecos_root() -> str:
    # hecos/modules/executor/dev_tools.py -> c:\Hecos
    return os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


def resolve_python_interpreter(custom_path: str = "") -> str:
    """Resolve python_env\\python.exe when available, else fallback to sys.executable."""
    if custom_path and os.path.isfile(custom_path):
        return os.path.abspath(custom_path)
    root = _find_hecos_root()
    env_py = os.path.join(root, "python_env", "python.exe" if os.name == "nt" else "bin/python")
    if os.path.isfile(env_py):
        return env_py
    return sys.executable


def _coerce_int(value, default: int, min_val: int, max_val: int) -> int:
    try:
        num = int(value)
    except (TypeError, ValueError):
        return default
    return max(min_val, min(max_val, num))


def project_tree_tool(path: str = "", max_depth: int = 3, default_workspace: str = "") -> str:
    """Builds a compact directory tree excluding cache/venv folders."""
    target = os.path.abspath(path.strip() if path else (default_workspace or os.getcwd()))
    depth_limit = _coerce_int(max_depth, default=3, min_val=1, max_val=6)

    if not os.path.exists(target):
        return f"[EXECUTOR] Directory not found: {target}"
    if not os.path.isdir(target):
        return f"[EXECUTOR] Path is not a directory: {target}"

    lines = [f"Project Tree: {target} (max_depth={depth_limit})"]
    max_lines = 250
    truncated = False

    def _walk(current_dir: str, prefix: str, depth: int):
        nonlocal truncated
        if depth > depth_limit or truncated:
            return
        try:
            entries = sorted(
                os.listdir(current_dir),
                key=lambda name: (0 if os.path.isdir(os.path.join(current_dir, name)) else 1, name.lower()),
            )
        except OSError as exc:
            lines.append(f"{prefix}[error: {exc}]")
            return

        visible = [e for e in entries if e not in _IGNORED_DIRS]
        for idx, name in enumerate(visible):
            if len(lines) >= max_lines:
                truncated = True
                return
            full = os.path.join(current_dir, name)
            is_last = (idx == len(visible) - 1)
            branch = "└── " if is_last else "├── "
            next_prefix = prefix + ("    " if is_last else "│   ")
            if os.path.isdir(full):
                lines.append(f"{prefix}{branch}{name}/")
                _walk(full, next_prefix, depth + 1)
            else:
                lines.append(f"{prefix}{branch}{name}")

    _walk(target, "", 1)
    if truncated:
        lines.append("... (tree truncated at 250 entries; pass a deeper sub-path or lower max_depth)")

    result = "\n".join(lines)
    AgentTracer.emit_action("project_tree", target, f"{len(lines) - 1} entries")
    return result


def search_code_tool(
    query: str,
    path: str = "",
    file_glob: str = "",
    default_workspace: str = "",
) -> str:
    """Fast recursive text search across code and config files."""
    if not query or not str(query).strip():
        return "[EXECUTOR] Search query cannot be empty."

    needle = str(query).strip()
    needle_lower = needle.lower()
    target = os.path.abspath(path.strip() if path else (default_workspace or _find_hecos_root()))
    glob_pat = file_glob.strip() if file_glob else ""

    if not os.path.exists(target):
        return f"[EXECUTOR] Search path not found: {target}"

    matches = []
    max_matches = 60
    scanned_files = 0

    def _scan_file(fpath: str, rel_label: str):
        nonlocal scanned_files
        if len(matches) >= max_matches:
            return
        if glob_pat and not fnmatch.fnmatch(os.path.basename(fpath), glob_pat):
            return
        try:
            if os.path.getsize(fpath) > 1024 * 1024:
                return
            with open(fpath, "rb") as fb:
                sample = fb.read(2048)
                if b"\x00" in sample:
                    return
            scanned_files += 1
            with open(fpath, "r", encoding="utf-8", errors="replace") as ft:
                for line_no, line in enumerate(ft, 1):
                    if needle_lower in line.lower():
                        snippet = line.rstrip("\r\n")
                        if len(snippet) > 160:
                            snippet = snippet[:157] + "..."
                        matches.append(f"{rel_label}:{line_no}: {snippet}")
                        if len(matches) >= max_matches:
                            return
        except OSError:
            return

    if os.path.isfile(target):
        _scan_file(target, os.path.basename(target))
    else:
        for root_dir, dirnames, filenames in os.walk(target):
            dirnames[:] = sorted(d for d in dirnames if d not in _IGNORED_DIRS)
            for fname in sorted(filenames):
                if len(matches) >= max_matches:
                    break
                full = os.path.join(root_dir, fname)
                rel = os.path.relpath(full, target)
                _scan_file(full, rel)
            if len(matches) >= max_matches:
                break

    if not matches:
        AgentTracer.emit_action("search_code", f"{needle} in {target}", "0 matches")
        return f"[EXECUTOR] No matches for '{needle}' in {target} ({scanned_files} files scanned)."

    header = f"Search results for '{needle}' in {target} ({len(matches)} match(es)):"
    footer = "\n... (results capped at 60 matches)" if len(matches) >= max_matches else ""
    out = header + "\n" + "\n".join(matches) + footer
    AgentTracer.emit_action("search_code", f"{needle} in {target}", f"{len(matches)} matches")
    return out


def check_syntax_tool(file_path: str) -> str:
    """Verify file syntax (Python AST/py_compile, JSON, YAML, or JS via node)."""
    abs_path = os.path.abspath(file_path)
    if not os.path.isfile(abs_path):
        return f"[EXECUTOR] File not found: {abs_path}"

    ext = os.path.splitext(abs_path)[1].lower()
    try:
        with open(abs_path, "r", encoding="utf-8") as f:
            source = f.read()

        if ext == ".py":
            ast.parse(source, filename=abs_path)
            py_compile.compile(abs_path, doraise=True)
            res = f"[EXECUTOR] SYNTAX OK (Python AST + py_compile): {abs_path}"
        elif ext == ".json":
            json.loads(source)
            res = f"[EXECUTOR] SYNTAX OK (JSON): {abs_path}"
        elif ext in (".yaml", ".yml"):
            import yaml
            yaml.safe_load(source)
            res = f"[EXECUTOR] SYNTAX OK (YAML): {abs_path}"
        elif ext in (".js", ".mjs", ".cjs"):
            node_bin = shutil.which("node")
            if not node_bin:
                return f"[EXECUTOR] Syntax check skipped for {abs_path}: 'node' executable is not installed on PATH."
            proc = subprocess.run([node_bin, "--check", abs_path], capture_output=True, text=True, timeout=15)
            if proc.returncode != 0:
                err = (proc.stderr or proc.stdout or "").strip()
                res = f"[EXECUTOR] SYNTAX ERROR (JavaScript): {abs_path}\n{err}"
            else:
                res = f"[EXECUTOR] SYNTAX OK (Node --check): {abs_path}"
        else:
            res = f"[EXECUTOR] No specialized syntax checker for extension '{ext or '(none)'}'. File exists ({len(source)} chars): {abs_path}"

        AgentTracer.emit_action("check_syntax", abs_path, res)
        return res
    except SyntaxError as exc:
        err = f"[EXECUTOR] SYNTAX ERROR in {abs_path} at line {exc.lineno}: {exc.msg}"
        AgentTracer.emit_action("check_syntax", abs_path, err)
        return err
    except Exception as exc:
        err = f"[EXECUTOR] SYNTAX ERROR in {abs_path}: {exc}"
        AgentTracer.emit_action("check_syntax", abs_path, err)
        return err


def _is_authorized_project_dir(path: str, allowed_roots: list[str]) -> bool:
    if not _is_safe_path(path):
        return False
    abs_target = os.path.abspath(path).lower()
    for root in allowed_roots:
        if root and abs_target.startswith(os.path.abspath(root).lower()):
            return True
    return False


def _collect_allowed_roots(default_workspace: str, hecos_root: str) -> list[str]:
    roots = [r for r in (default_workspace, hecos_root) if r]
    try:
        cfg_mgr = getattr(sys, "hecos_config_manager", None)
        if cfg_mgr:
            paths = cfg_mgr.get_plugin_config("EXECUTOR", "important_paths", {}) or {}
            if isinstance(paths, dict):
                for val in paths.values():
                    if isinstance(val, str) and val.strip():
                        roots.append(val.strip())
    except Exception:
        pass
    return roots


def run_project_test_tool(
    target_path_or_command: str,
    cwd: str = "",
    timeout_seconds: Optional[int] = None,
    default_workspace: str = "",
    custom_python: str = "",
) -> str:
    """
    Runs a Python script, unittest, or pytest target inside an authorized project directory
    using python_env\\python.exe without the AST jail restrictions of sandbox.py.
    """
    hecos_root = _find_hecos_root()
    allowed_roots = _collect_allowed_roots(default_workspace, hecos_root)

    work_dir = os.path.abspath(cwd.strip() if cwd else (default_workspace or hecos_root))
    if not os.path.isdir(work_dir):
        return f"[EXECUTOR] Working directory does not exist: {work_dir}"
    if not _is_authorized_project_dir(work_dir, allowed_roots):
        return f"[EXECUTOR] ACCESS DENIED: '{work_dir}' is outside authorized workspace/project paths."

    if timeout_seconds is None:
        try:
            cfg_mgr = getattr(sys, "hecos_config_manager", None)
            timeout_seconds = cfg_mgr.get_plugin_config("EXECUTOR", "test_timeout_seconds", 30) if cfg_mgr else 30
        except Exception:
            timeout_seconds = 30
    timeout = _coerce_int(timeout_seconds, default=30, min_val=5, max_val=180)

    if not custom_python:
        try:
            cfg_mgr = getattr(sys, "hecos_config_manager", None)
            custom_python = cfg_mgr.get_plugin_config("EXECUTOR", "python_interpreter", "") if cfg_mgr else ""
        except Exception:
            custom_python = ""
    py_exe = resolve_python_interpreter(custom_python)

    raw_cmd = (target_path_or_command or "").strip()
    if not raw_cmd:
        return "[EXECUTOR] Please provide a script path or test command (e.g. 'main.py' or '-m unittest discover')."

    pp_roots = os.pathsep.join([p for p in (work_dir, hecos_root) if p])

    def _wrap_script(script_path: str, extra_args: list[str]) -> list[str]:
        boot = (
            "import os, sys, runpy; "
            "sys.path[:0] = [p for p in sys.argv[1].split(os.pathsep) if p and p not in sys.path]; "
            "target = sys.argv[2]; sys.argv = [target, *sys.argv[3:]]; "
            "runpy.run_path(target, run_name='__main__')"
        )
        return [py_exe, "-c", boot, pp_roots, script_path, *extra_args]

    def _wrap_module(mod_name: str, extra_args: list[str]) -> list[str]:
        boot = (
            "import os, sys, runpy; "
            "sys.path[:0] = [p for p in sys.argv[1].split(os.pathsep) if p and p not in sys.path]; "
            "mod = sys.argv[2]; sys.argv = [mod, *sys.argv[3:]]; "
            "runpy.run_module(mod, run_name='__main__', alter_sys=True)"
        )
        return [py_exe, "-c", boot, pp_roots, mod_name, *extra_args]

    candidate_file = os.path.abspath(raw_cmd) if os.path.isabs(raw_cmd) else os.path.abspath(os.path.join(work_dir, raw_cmd))
    if os.path.isfile(candidate_file):
        if not _is_authorized_project_dir(candidate_file, allowed_roots):
            return f"[EXECUTOR] ACCESS DENIED: Target script '{candidate_file}' is outside authorized paths."
        cmd_list = _wrap_script(candidate_file, [])
        display_cmd = f"{py_exe} {candidate_file}"
    else:
        try:
            parts = shlex.split(raw_cmd, posix=(os.name != "nt"))
        except ValueError as exc:
            return f"[EXECUTOR] Invalid command syntax: {exc}"
        if not parts:
            return "[EXECUTOR] Empty command."
        first = parts[0].lower()
        rest = parts[1:]
        if first in ("python", "python3", "py"):
            if rest and rest[0] == "-m" and len(rest) >= 2:
                cmd_list = _wrap_module(rest[1], rest[2:])
            elif rest and rest[0].endswith(".py"):
                script_arg = os.path.abspath(rest[0]) if os.path.isabs(rest[0]) else os.path.abspath(os.path.join(work_dir, rest[0]))
                if not _is_authorized_project_dir(script_arg, allowed_roots):
                    return f"[EXECUTOR] ACCESS DENIED: Target script '{script_arg}' is outside authorized paths."
                cmd_list = _wrap_script(script_arg, rest[1:])
            else:
                cmd_list = [py_exe, *rest]
        elif first == "pytest":
            cmd_list = _wrap_module("pytest", rest)
        elif first == "-m" and rest:
            cmd_list = _wrap_module(rest[0], rest[1:])
        elif first.endswith(".py"):
            script_arg = os.path.abspath(parts[0]) if os.path.isabs(parts[0]) else os.path.abspath(os.path.join(work_dir, parts[0]))
            if not _is_authorized_project_dir(script_arg, allowed_roots):
                return f"[EXECUTOR] ACCESS DENIED: Target script '{script_arg}' is outside authorized paths."
            cmd_list = _wrap_script(script_arg, rest)
        else:
            return (
                "[EXECUTOR] run_project_test supports Python scripts (.py), 'pytest ...', "
                "or 'python -m ...' invocations. For general OS commands use execute_shell_command."
            )
        display_cmd = f"{py_exe} {raw_cmd}"

    env = os.environ.copy()
    existing_pp = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{pp_roots}{os.pathsep}{existing_pp}" if existing_pp else pp_roots

    try:
        proc = subprocess.run(
            cmd_list,
            cwd=work_dir,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        stdout_tail = (proc.stdout or "")[-3000:].strip()
        stderr_tail = (proc.stderr or "")[-2000:].strip()
        parts_out = [
            f"Exit Code: {proc.returncode}",
            f"CWD: {work_dir}",
            f"Command: {display_cmd}",
        ]
        if stdout_tail:
            parts_out.append(f"--- STDOUT ---\n{stdout_tail}")
        if stderr_tail:
            parts_out.append(f"--- STDERR ---\n{stderr_tail}")
        if not stdout_tail and not stderr_tail:
            parts_out.append("(no output)")
        output = "\n".join(parts_out)
        AgentTracer.emit_action("run_project_test", raw_cmd, f"exit={proc.returncode}")
        return output
    except subprocess.TimeoutExpired:
        msg = f"[EXECUTOR] Test timed out after {timeout}s: {raw_cmd}"
        AgentTracer.emit_action("run_project_test", raw_cmd, msg)
        return msg
    except Exception as exc:
        msg = f"[EXECUTOR] Test execution error: {exc}"
        AgentTracer.emit_action("run_project_test", raw_cmd, msg)
        return msg
