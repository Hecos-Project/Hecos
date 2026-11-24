"""
hecos/modules/executor/dev_tools.py
Project navigation, code search, syntax verification, and real project test runner
for Hecos EXECUTOR (separate from the isolated AST jail in sandbox.py).
"""

import ast
import json
import os
import py_compile
import re
import shlex
import shutil
import subprocess
import sys
from typing import List, Optional

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
    """AST-aware recursive code search (via grep-ast + .gitignore support) across a project directory."""
    if not query or not str(query).strip():
        return "[EXECUTOR] Search query cannot be empty."

    needle = str(query).strip()
    target = os.path.abspath(path.strip() if path else (default_workspace or _find_hecos_root()))
    glob_pat = file_glob.strip() if file_glob else ""

    if not os.path.exists(target):
        return f"[EXECUTOR] Search path not found: {target}"

    from .code_intel import ast_search_code

    out = ast_search_code(needle, target, file_glob=glob_pat, case_sensitive=False, max_matches=35)
    AgentTracer.emit_action("search_code", f"{needle} in {target}", "completed")
    return out


def check_syntax_tool(file_path: str) -> str:
    """Verify syntax and static sanity (Python AST/py_compile + Ruff, JSON, YAML, or JS/TS/CSS/HTML via node/tree-sitter)."""
    abs_path = os.path.abspath(file_path)
    if not os.path.isfile(abs_path):
        return f"[EXECUTOR] File not found: {abs_path}"

    ext = os.path.splitext(abs_path)[1].lower()
    try:
        with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
            source = f.read()

        if ext == ".py":
            ast.parse(source, filename=abs_path)
            py_compile.compile(abs_path, doraise=True)
            from .code_intel import run_ruff_check

            ruff_ok, ruff_errors, ruff_warnings = run_ruff_check(abs_path)
            if not ruff_ok and ruff_errors:
                err_lines = "\n".join(f"  - {e}" for e in ruff_errors)
                err = f"[EXECUTOR] SYNTAX ERROR / STATIC BUG (Ruff) in {abs_path}:\n{err_lines}"
                logger.warning(err)
                AgentTracer.emit_action("check_syntax", abs_path, err)
                return err
            res = f"[EXECUTOR] SYNTAX OK (Python AST + py_compile + Ruff): {abs_path}"
            if ruff_warnings:
                res += "\n[RUFF-WARN] " + "; ".join(ruff_warnings[:5])
        elif ext == ".json":
            json.loads(source)
            res = f"[EXECUTOR] SYNTAX OK (JSON): {abs_path}"
        elif ext in (".yaml", ".yml"):
            import yaml
            yaml.safe_load(source)
            res = f"[EXECUTOR] SYNTAX OK (YAML): {abs_path}"
        elif ext in (".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".css", ".html", ".htm"):
            node_bin = shutil.which("node")
            if node_bin and ext in (".js", ".mjs", ".cjs"):
                proc = subprocess.run([node_bin, "--check", abs_path], capture_output=True, text=True, timeout=15)
                if proc.returncode != 0:
                    err = (proc.stderr or proc.stdout or "").strip()
                    res = f"[EXECUTOR] SYNTAX ERROR (JavaScript): {abs_path}\n{err}"
                else:
                    res = f"[EXECUTOR] SYNTAX OK (Node --check): {abs_path}"
            else:
                from .code_intel import check_tree_sitter_syntax

                ts_err = check_tree_sitter_syntax(abs_path, source)
                if ts_err:
                    res = f"[EXECUTOR] SYNTAX ERROR ({ext.lstrip('.').upper()} tree-sitter): {abs_path}\n  {ts_err}"
                else:
                    res = f"[EXECUTOR] SYNTAX OK (Tree-sitter {ext}): {abs_path}"
        else:
            res = f"[EXECUTOR] No specialized syntax checker for extension '{ext or '(none)'}'. File exists ({len(source)} chars): {abs_path}"

        logger.debug(f"[EXECUTOR] check_syntax OK: {abs_path} ({ext or 'noext'})")
        AgentTracer.emit_action("check_syntax", abs_path, res)
        return res
    except SyntaxError as exc:
        err = f"[EXECUTOR] SYNTAX ERROR in {abs_path} at line {exc.lineno}: {exc.msg}"
        logger.warning(err)
        AgentTracer.emit_action("check_syntax", abs_path, err)
        return err
    except Exception as exc:
        err = f"[EXECUTOR] SYNTAX ERROR in {abs_path}: {exc}"
        logger.warning(err)
        AgentTracer.emit_action("check_syntax", abs_path, err)
        return err


_FLASK_RENDER_TPL_RE = re.compile(r"render_template\(\s*['\"]([^'\"]+)['\"]")
_FLASK_INIT_RE = re.compile(r"Flask\(([^)]*)\)")
_HTML_LOCAL_ASSET_RE = re.compile(
    r"""<(?:link|script)\b[^>]*\b(?:href|src)=['"]([^'"]+)['"]""",
    re.IGNORECASE,
)


def _extract_flask_init_args(py_text: str) -> Optional[str]:
    m = _FLASK_INIT_RE.search(py_text or "")
    return m.group(1) if m else None


def _detect_flask_top_level_run(py_txt: str) -> Optional[tuple[int, List[int]]]:
    """
    Detect unguarded module-level `*.run(...)` calls outside `if __name__ == '__main__':`.
    Returns (run_line, later_route_lines) if an unguarded `.run()` is present.
    """
    try:
        tree = ast.parse(py_txt)
    except SyntaxError:
        return None

    route_lines: List[int] = []
    top_run_lines: List[int] = []

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for dec in node.decorator_list:
                if (
                    isinstance(dec, ast.Call)
                    and isinstance(dec.func, ast.Attribute)
                    and dec.func.attr in {"route", "get", "post", "put", "patch", "delete"}
                ):
                    route_lines.append(node.lineno)
        elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            fn = node.value.func
            if isinstance(fn, ast.Attribute):
                if fn.attr == "run":
                    top_run_lines.append(node.lineno)
                elif fn.attr == "add_url_rule":
                    route_lines.append(node.lineno)

    if not top_run_lines:
        return None
    first_run = min(top_run_lines)
    later_routes = sorted(ln for ln in route_lines if ln > first_run)
    return first_run, later_routes


def inspect_web_project_issues(abs_path: str) -> List[str]:
    """
    Detect common Flask/HTML project wiring mistakes immediately after write/patch
    (e.g., render_template() with index.html in project root instead of templates/,
    relative CSS/JS links without Flask static configuration, or debug=True reloader).
    """
    ext = os.path.splitext(abs_path)[1].lower()
    if ext not in {".py", ".html", ".htm"} or not os.path.isfile(abs_path):
        return []

    file_dir = os.path.dirname(abs_path)
    proj_dir = (
        os.path.dirname(file_dir)
        if os.path.basename(file_dir).lower() in {"templates", "static"}
        else file_dir
    )
    if not os.path.isdir(proj_dir):
        return []

    warnings: List[str] = []
    py_sources: List[tuple[str, str]] = []
    try:
        for fname in sorted(os.listdir(proj_dir)):
            if fname.endswith(".py"):
                fpath = os.path.join(proj_dir, fname)
                if os.path.isfile(fpath) and os.path.getsize(fpath) <= 131072:
                    with open(fpath, "r", encoding="utf-8", errors="replace") as fh:
                        py_sources.append((fpath, fh.read()))
    except OSError:
        return []

    has_flask = False
    default_tpl_flask = False
    default_static_flask = False

    for fpath, py_txt in py_sources:
        init_args = _extract_flask_init_args(py_txt)
        if init_args is None:
            continue
        has_flask = True
        uses_default_tpl = "template_folder" not in init_args
        uses_default_static = (
            "static_folder" not in init_args
            and "send_from_directory" not in py_txt
            and "send_file" not in py_txt
        )
        default_tpl_flask = default_tpl_flask or uses_default_tpl
        default_static_flask = default_static_flask or uses_default_static

        if uses_default_tpl:
            for tpl_name in sorted(set(_FLASK_RENDER_TPL_RE.findall(py_txt))):
                rel_tpl = tpl_name.lstrip("/\\")
                expected_tpl = os.path.join(proj_dir, "templates", rel_tpl)
                root_fallback = os.path.join(proj_dir, rel_tpl)
                if not os.path.isfile(expected_tpl) and os.path.isfile(root_fallback):
                    warnings.append(
                        f"Flask template mismatch in {os.path.basename(fpath)}: "
                        f"render_template('{tpl_name}') looks for 'templates/{rel_tpl}' (missing), "
                        f"while '{rel_tpl}' was written in '{proj_dir}'. Move HTML into 'templates/' "
                        "or initialize Flask(__name__, template_folder='.', static_folder='.', static_url_path='')."
                    )
                elif os.path.isfile(expected_tpl) and os.path.isfile(root_fallback):
                    warnings.append(
                        f"Duplicate template conflict in {os.path.basename(fpath)}: BOTH 'templates/{rel_tpl}' "
                        f"and root '{rel_tpl}' exist! Flask render_template() uses 'templates/{rel_tpl}' and ignores root '{rel_tpl}' "
                        "unless template_folder='.'. Keep only one active template."
                    )
        else:
            tpl_dot = bool(re.search(r"template_folder\s*=\s*['\"]\.['\"]", init_args))
            if tpl_dot:
                for tpl_name in sorted(set(_FLASK_RENDER_TPL_RE.findall(py_txt))):
                    rel_tpl = tpl_name.lstrip("/\\")
                    root_tpl = os.path.join(proj_dir, rel_tpl)
                    sub_tpl = os.path.join(proj_dir, "templates", rel_tpl)
                    if not os.path.isfile(root_tpl) and os.path.isfile(sub_tpl):
                        warnings.append(
                            f"Flask template mismatch in {os.path.basename(fpath)}: "
                            f"template_folder='.' looks for '{rel_tpl}' in project root (missing), "
                            f"while '{tpl_name}' exists under 'templates/{rel_tpl}'! "
                            "Move index.html to project root OR use template_folder='templates'."
                        )

        if ext == ".py" and os.path.normcase(fpath) == os.path.normcase(abs_path):
            top_run_info = _detect_flask_top_level_run(py_txt)
            if top_run_info:
                run_line, later_routes = top_run_info
                if later_routes:
                    warnings.append(
                        f"Critical Flask route/import bug in {os.path.basename(fpath)} line {run_line}: "
                        f"'.run()' executes at module import time BEFORE @route definitions on lines {later_routes[:6]}, "
                        "so Flask starts with 0 routes (HTTP 404) and blocks test imports! "
                        "Move app.run(...) inside 'if __name__ == \"__main__\":' at the bottom of the file."
                    )
                else:
                    warnings.append(
                        f"Flask import-blocking bug in {os.path.basename(fpath)} line {run_line}: "
                        "'.run()' is called at module top level outside 'if __name__ == \"__main__\":', "
                        "which blocks pytest/unittest imports until timeout. Wrap it in 'if __name__ == \"__main__\":'."
                    )
            if re.search(r"\.run\([^)]*debug\s*=\s*True", py_txt) and "use_reloader" not in py_txt:
                warnings.append(
                    f"Flask reloader note in {os.path.basename(fpath)}: "
                    "app.run(debug=True) spawns a child reloader process; prefer debug=False or use_reloader=False "
                    "when launching via EXECUTOR__start_app for clean logs and PID control."
                )

    if has_flask and default_static_flask:
        html_candidates: List[str] = []
        for candidate_dir in (proj_dir, os.path.join(proj_dir, "templates")):
            if os.path.isdir(candidate_dir):
                try:
                    for fn in sorted(os.listdir(candidate_dir)):
                        if fn.lower().endswith((".html", ".htm")):
                            html_candidates.append(os.path.join(candidate_dir, fn))
                except OSError:
                    pass

        bad_assets: List[str] = []
        for html_path in html_candidates:
            try:
                if os.path.getsize(html_path) > 131072:
                    continue
                with open(html_path, "r", encoding="utf-8", errors="replace") as fh:
                    html_txt = fh.read()
            except OSError:
                continue
            for ref in _HTML_LOCAL_ASSET_RE.findall(html_txt):
                low = ref.strip().lower()
                if not low or low.startswith(("http://", "https://", "//", "data:", "#", "{{", "/static/", "static/")):
                    continue
                if low.endswith((".css", ".js", ".mjs", ".png", ".jpg", ".jpeg", ".svg", ".webp")):
                    if ref not in bad_assets:
                        bad_assets.append(ref)

        if bad_assets:
            warnings.append(
                f"Static asset 404 risk in HTML ({', '.join(bad_assets[:6])}): "
                "Flask(__name__) only serves files under '/static/' by default. "
                "Use Flask(__name__, static_folder='.', static_url_path='') OR move CSS/JS to 'static/' "
                "and reference them as '/static/...'."
            )

    if ext in {".html", ".htm"}:
        try:
            with open(abs_path, "r", encoding="utf-8", errors="replace") as fh:
                own_html = fh.read()
            has_img = bool(re.search(r"<img\b", own_html, re.IGNORECASE))
            has_img_bound = bool(re.search(r"img\b[^}]*(?:max-width|max-height|width\s*:)", own_html, re.IGNORECASE | re.DOTALL))
            has_rigid_vh = bool(re.search(r"(?<!min-)height\s*:\s*100vh", own_html, re.IGNORECASE))
            if has_img and not has_img_bound and has_rigid_vh:
                warnings.append(
                    f"Responsive media layout warning in {os.path.basename(abs_path)}: "
                    "unconstrained <img> inside 'height: 100vh' centering can push header/controls off-screen. "
                    "Use 'min-height: 100vh' and constrain img (e.g. 'max-width: 100%; max-height: 60vh; height: auto;')."
                )
            if has_flask and re.search(r"""(?:src|href|poster)=['"](?:file://|[A-Za-z]:[/\\])""", own_html, re.IGNORECASE):
                warnings.append(
                    f"Local filesystem path warning in {os.path.basename(abs_path)}: "
                    "browsers block raw 'file://' or 'C:/...' media paths on http://127.0.0.1. "
                    "Copy media into the project folder or add a Flask route serving the image."
                )
        except OSError:
            pass

    if ext in {".html", ".htm"}:
        from .code_intel import check_static_web_assets

        for asset_err in check_static_web_assets(abs_path):
            if asset_err not in warnings:
                warnings.append(asset_err)

    for w in warnings:
        logger.warning(f"[EXECUTOR] Web diagnostic: {w}")
    return warnings


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

    logger.info(f"[EXECUTOR] run_project_test start: cwd={work_dir} cmd={display_cmd} timeout={timeout}s")
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
        logger.info(
            f"[EXECUTOR] run_project_test done: exit={proc.returncode} stdout={len(proc.stdout or '')}B stderr={len(proc.stderr or '')}B"
        )
        AgentTracer.emit_action("run_project_test", raw_cmd, f"exit={proc.returncode}")
        return output
    except subprocess.TimeoutExpired:
        msg = f"[EXECUTOR] Test timed out after {timeout}s: {raw_cmd}"
        logger.warning(msg)
        AgentTracer.emit_action("run_project_test", raw_cmd, msg)
        return msg
    except Exception as exc:
        msg = f"[EXECUTOR] Test execution error: {exc}"
        logger.error(msg)
        AgentTracer.emit_action("run_project_test", raw_cmd, msg)
        return msg
