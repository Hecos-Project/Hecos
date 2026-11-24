"""
hecos/modules/executor/test_runner.py
Workspace target authorization, script invocation builders, test discovery/execution,
and workspace project cataloging for Hecos EXECUTOR and WebUI Workspace Runner.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional

from .dev_tools import (
    _IGNORED_DIRS,
    _coerce_int,
    _collect_allowed_roots,
    _find_hecos_root,
    _is_authorized_project_dir,
    resolve_python_interpreter,
)
from .file_manager import AgentTracer, logger

_RUNNABLE_EXTS = {".py", ".bat", ".cmd", ".sh"}
_ENTRY_PRIORITY = ("main.py", "app.py", "run.py", "server.py", "cli.py", "index.py")


def is_test_filename(filename: str) -> bool:
    """Return True if filename follows unittest/pytest naming conventions."""
    low = os.path.basename(filename).lower()
    return low.endswith(".py") and (low.startswith("test_") or low.endswith("_test.py"))


def collect_strict_workspace_roots(workspace_dir: str) -> List[str]:
    """Authorize execution strictly within the user's workspace/projects folders."""
    roots: List[str] = []
    if workspace_dir:
        roots.append(os.path.abspath(workspace_dir))
    try:
        cfg_mgr = getattr(sys, "hecos_config_manager", None)
        if cfg_mgr:
            paths = cfg_mgr.get_plugin_config("EXECUTOR", "important_paths", {}) or {}
            if isinstance(paths, dict):
                proj = (paths.get("projects") or "").strip()
                norm = proj.replace("\\", "/").rstrip("/")
                if proj and norm not in {"./workspace", "workspace", "workspace/sandbox", "./workspace/sandbox"}:
                    if os.path.isabs(proj):
                        roots.append(os.path.abspath(proj))
    except Exception:
        pass
    return roots


def resolve_authorized_target(
    target_path: str,
    workspace_dir: str,
    *,
    strict_workspace_only: bool = True,
) -> tuple[Optional[str], Optional[str]]:
    """
    Resolve a relative or absolute path and enforce containment within authorized roots.
    Returns (abs_path, error_message).
    """
    from .file_manager import sanitize_llm_path

    clean = sanitize_llm_path(target_path)
    if not clean:
        return None, "Target path cannot be empty."

    ws_abs = os.path.abspath(workspace_dir)
    candidate = os.path.abspath(clean) if os.path.isabs(clean) else os.path.abspath(os.path.join(ws_abs, clean))

    allowed_roots = (
        collect_strict_workspace_roots(ws_abs)
        if strict_workspace_only
        else _collect_allowed_roots(ws_abs, _find_hecos_root())
    )
    if not _is_authorized_project_dir(candidate, allowed_roots):
        return None, f"Access denied: '{candidate}' is outside authorized workspace paths."
    if not os.path.exists(candidate):
        hint = ""
        if not os.path.isabs(clean) and os.path.isdir(ws_abs):
            fname = os.path.basename(candidate)
            matches: List[str] = []
            try:
                for entry in sorted(os.listdir(ws_abs)):
                    sub_dir = os.path.join(ws_abs, entry)
                    if os.path.isdir(sub_dir) and os.path.exists(os.path.join(sub_dir, fname)):
                        matches.append(f"{entry}/{fname}")
                        if len(matches) >= 4:
                            break
            except OSError:
                pass
            if matches:
                hint = f" (Found in workspace subfolder(s): {', '.join(matches)}. Pass the full subfolder path.)"
        return None, f"Path not found: {candidate}{hint}"
    return candidate, None


def _build_python_script_cmd(
    py_exe: str,
    script_path: str,
    extra_args: List[str],
    import_roots: List[str],
) -> List[str]:
    pp_roots = os.pathsep.join([os.path.abspath(p) for p in import_roots if p])
    boot = (
        "import os, sys, runpy; "
        "sys.path[:0] = [p for p in sys.argv[1].split(os.pathsep) if p and p not in sys.path]; "
        "target = sys.argv[2]; sys.argv = [target, *sys.argv[3:]]; "
        "runpy.run_path(target, run_name='__main__')"
    )
    return [py_exe, "-c", boot, pp_roots, os.path.abspath(script_path), *extra_args]


def _build_python_module_cmd(
    py_exe: str,
    mod_name: str,
    extra_args: List[str],
    import_roots: List[str],
) -> List[str]:
    pp_roots = os.pathsep.join([os.path.abspath(p) for p in import_roots if p])
    boot = (
        "import os, sys, runpy; "
        "sys.path[:0] = [p for p in sys.argv[1].split(os.pathsep) if p and p not in sys.path]; "
        "mod = sys.argv[2]; sys.argv = [mod, *sys.argv[3:]]; "
        "runpy.run_module(mod, run_name='__main__', alter_sys=True)"
    )
    return [py_exe, "-c", boot, pp_roots, mod_name, *extra_args]


def _collect_workspace_import_roots(base_dir: str, workspace_dir: str, extra_dir: str = "") -> List[str]:
    """Collect deduplicated Python import roots from base_dir/extra_dir up to workspace_dir."""
    ws_abs = os.path.abspath(workspace_dir)
    roots: List[str] = []
    seen = set()

    def _add(path: str) -> None:
        if not path:
            return
        abs_p = os.path.abspath(path)
        key = os.path.normcase(abs_p)
        if key not in seen:
            seen.add(key)
            roots.append(abs_p)

    for seed in (extra_dir, base_dir):
        if not seed:
            continue
        cur = os.path.abspath(seed)
        while True:
            _add(cur)
            try:
                if os.path.normcase(cur) == os.path.normcase(ws_abs):
                    break
                if os.path.normcase(os.path.commonpath([cur, ws_abs])) != os.path.normcase(ws_abs):
                    break
            except ValueError:
                break
            parent = os.path.dirname(cur)
            if not parent or parent == cur:
                break
            cur = parent

    _add(ws_abs)
    return roots


def _build_script_invocation(
    target_path: str,
    extra_args: List[str],
    workspace_dir: str,
) -> tuple[Optional[List[str]], str, str, Optional[str]]:
    """Build subprocess command list, working directory, display command, and optional error."""
    ext = os.path.splitext(target_path)[1].lower()
    if ext not in _RUNNABLE_EXTS:
        return None, "", "", f"Unsupported executable extension '{ext or '(none)'}'."

    ws_abs = os.path.abspath(workspace_dir)
    target_dir = os.path.dirname(target_path) if os.path.isfile(target_path) else target_path
    work_dir = ws_abs if os.path.normcase(target_dir) == os.path.normcase(ws_abs) else target_dir
    import_roots = _collect_workspace_import_roots(work_dir, ws_abs)

    if ext == ".py":
        py_exe = resolve_python_interpreter()
        cmd = _build_python_script_cmd(py_exe, target_path, extra_args, import_roots)
        display = f"{os.path.basename(py_exe)} {os.path.basename(target_path)}"
        if extra_args:
            display += " " + " ".join(extra_args)
        return cmd, work_dir, display, None

    if ext in {".bat", ".cmd"} and os.name == "nt":
        cmd = ["cmd.exe", "/c", target_path, *extra_args]
        return cmd, work_dir, os.path.basename(target_path), None

    if ext == ".sh" and os.name != "nt":
        cmd = ["sh", target_path, *extra_args]
        return cmd, work_dir, os.path.basename(target_path), None

    return None, "", "", f"Cannot execute '{ext}' script on platform '{os.name}'."


def find_project_tests(target_path: str, workspace_dir: str) -> tuple[List[str], str]:
    """
    Locate matching test files for a module file or project folder inside workspace_dir.
    Returns (sorted_test_files, project_root_dir).
    """
    ws_abs = os.path.abspath(workspace_dir)
    abs_target = os.path.abspath(target_path)

    if os.path.isdir(abs_target):
        project_root = abs_target
        matches: List[str] = []
        for root_dir, dirnames, filenames in os.walk(project_root):
            dirnames[:] = sorted(d for d in dirnames if d not in _IGNORED_DIRS)
            for fname in sorted(filenames):
                if is_test_filename(fname):
                    matches.append(os.path.join(root_dir, fname))
        return matches, project_root

    target_dir = os.path.dirname(abs_target)
    fname = os.path.basename(abs_target)
    if is_test_filename(fname):
        return [abs_target], target_dir

    if os.path.normcase(target_dir) == os.path.normcase(ws_abs):
        stem = os.path.splitext(fname)[0]
        candidates = [
            os.path.join(ws_abs, f"test_{stem}.py"),
            os.path.join(ws_abs, f"{stem}_test.py"),
            os.path.join(ws_abs, "tests", f"test_{stem}.py"),
            os.path.join(ws_abs, "tests", f"{stem}_test.py"),
        ]
        return [p for p in candidates if os.path.isfile(p)], ws_abs

    matches = []
    for root_dir, dirnames, filenames in os.walk(target_dir):
        dirnames[:] = sorted(d for d in dirnames if d not in _IGNORED_DIRS)
        for item in sorted(filenames):
            if is_test_filename(item):
                matches.append(os.path.join(root_dir, item))
    return matches, target_dir


def _build_subproc_env(import_roots: List[str]) -> Dict[str, str]:
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    pp_roots = os.pathsep.join([os.path.abspath(p) for p in import_roots if p])
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{pp_roots}{os.pathsep}{existing}" if existing else pp_roots
    return env


def _compute_discover_top_dir(start_dir: str, workspace_root: str) -> str:
    """Walk upward while folders are packages (__init__.py) without crossing workspace_root."""
    top = os.path.abspath(start_dir)
    ws_norm = os.path.normcase(os.path.abspath(workspace_root))
    while os.path.isfile(os.path.join(top, "__init__.py")):
        parent = os.path.dirname(top)
        if not parent or parent == top:
            break
        top = parent
        if os.path.normcase(top) == ws_norm:
            break
    return top


def _build_bare_pytest_fallback_cmd(
    py_exe: str,
    test_files: List[str],
    import_roots: List[str],
) -> List[str]:
    """Run top-level test_*() functions for plain assert-based test files when pytest is absent."""
    pp_roots = os.pathsep.join([os.path.abspath(p) for p in import_roots if p])
    runner = (
        "import importlib.util, inspect, os, sys, traceback; "
        "sys.path[:0] = [p for p in sys.argv[1].split(os.pathsep) if p and p not in sys.path]; "
        "files = sys.argv[2:]; ran = 0; failed = 0\n"
        "for fp in files:\n"
        "    spec = importlib.util.spec_from_file_location('hecos_plain_test_' + str(ran), fp)\n"
        "    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)\n"
        "    for name, fn in inspect.getmembers(mod, inspect.isfunction):\n"
        "        if name.startswith('test_') and fn.__module__ == mod.__name__ and not inspect.signature(fn).parameters:\n"
        "            ran += 1\n"
        "            try:\n"
        "                fn(); print(f'{os.path.basename(fp)}::{name} ... ok')\n"
        "            except Exception:\n"
        "                failed += 1; print(f'{os.path.basename(fp)}::{name} ... FAIL'); traceback.print_exc()\n"
        "print(f'----------------------------------------------------------------------\\nRan {ran} function test(s)'); "
        "sys.exit(1 if failed or ran == 0 else 0)"
    )
    return [py_exe, "-c", runner, pp_roots, *test_files]


def run_tests_for_target(
    target_path: str,
    workspace_dir: str,
    *,
    timeout_seconds: int = 30,
    strict_workspace_only: bool = True,
) -> Dict[str, Any]:
    """Discover and execute unittest suites (with plain test_* fallback) for a target path."""
    abs_target, err = resolve_authorized_target(
        target_path, workspace_dir, strict_workspace_only=strict_workspace_only
    )
    if err:
        return {"ok": False, "status": "error", "error": err, "output": err}

    test_files, project_root = find_project_tests(abs_target, workspace_dir)
    if not test_files:
        msg = (
            f"No test files (test_*.py / *_test.py) found for '{os.path.basename(abs_target)}'. "
            "You can generate unit tests with Hecos Coder first."
        )
        return {
            "ok": False,
            "status": "no_tests",
            "no_tests_found": True,
            "path": abs_target,
            "error": msg,
            "output": msg,
        }

    ws_abs = os.path.abspath(workspace_dir)
    py_exe = resolve_python_interpreter()
    timeout = _coerce_int(timeout_seconds, default=30, min_val=5, max_val=180)
    extra_test_dir = os.path.dirname(test_files[0]) if len(test_files) == 1 else ""
    import_roots = _collect_workspace_import_roots(project_root, ws_abs, extra_dir=extra_test_dir)

    if len(test_files) == 1:
        test_file = test_files[0]
        start_dir = os.path.dirname(test_file)
        pattern = os.path.basename(test_file)
        top_dir = _compute_discover_top_dir(start_dir, ws_abs)
        discover_args = ["discover", "-s", start_dir, "-p", pattern, "-t", top_dir, "-v"]
        display = f"python -m unittest discover -s {os.path.relpath(start_dir, ws_abs)} -p {pattern} -v"
    else:
        top_dir = _compute_discover_top_dir(project_root, ws_abs)
        discover_args = ["discover", "-s", project_root, "-t", top_dir, "-v"]
        display = f"python -m unittest discover -s {os.path.relpath(project_root, ws_abs)} -v"

    cmd = _build_python_module_cmd(py_exe, "unittest", discover_args, import_roots)
    env = _build_subproc_env(import_roots)
    popen_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

    started = time.perf_counter()
    logger.info(f"[RUNNER] test_runner start target={abs_target} files={len(test_files)} cmd={display}")
    try:
        proc = subprocess.run(
            cmd,
            cwd=project_root,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            creationflags=popen_flags,
        )
        combined = "\n".join(p.strip() for p in (proc.stdout, proc.stderr) if p and p.strip())

        if proc.returncode == 0 and "Ran 0 tests" in combined:
            fb_cmd = _build_bare_pytest_fallback_cmd(py_exe, test_files, import_roots)
            fb_proc = subprocess.run(
                fb_cmd,
                cwd=project_root,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                creationflags=popen_flags,
            )
            fb_out = "\n".join(p.strip() for p in (fb_proc.stdout, fb_proc.stderr) if p and p.strip())
            if fb_proc.returncode == 0 or "FAIL" in fb_out or "Ran 0 function test(s)" not in fb_out:
                proc = fb_proc
                combined = fb_out
                display = f"python -c <function-test-runner> ({len(test_files)} file(s))"

        duration_ms = int((time.perf_counter() - started) * 1000)
        combined = (combined or "(no output)")[-8000:]
        logger.info(
            f"[RUNNER] test_runner done target={os.path.basename(abs_target)} exit={proc.returncode} duration_ms={duration_ms}"
        )
        AgentTracer.emit_action("test_runner", os.path.basename(abs_target), f"exit={proc.returncode} ({duration_ms}ms)")
        return {
            "ok": proc.returncode == 0,
            "status": "passed" if proc.returncode == 0 else "failed",
            "execution_type": "test",
            "path": abs_target,
            "test_files": test_files,
            "cwd": project_root,
            "command": display,
            "exit_code": proc.returncode,
            "duration_ms": duration_ms,
            "output": combined,
        }
    except subprocess.TimeoutExpired:
        duration_ms = int((time.perf_counter() - started) * 1000)
        msg = f"Test execution timed out after {timeout}s."
        return {
            "ok": False,
            "status": "timeout",
            "execution_type": "test",
            "path": abs_target,
            "command": display,
            "exit_code": None,
            "duration_ms": duration_ms,
            "output": msg,
            "error": msg,
        }
    except Exception as exc:
        msg = f"Test execution failed: {exc}"
        return {"ok": False, "status": "error", "path": abs_target, "output": msg, "error": msg}


def list_workspace_projects(workspace_dir: str, registry=None) -> List[Dict[str, Any]]:
    """Catalog projects and runnable scripts in workspace_dir for the Workspace Runner UI."""
    ws_abs = os.path.abspath(workspace_dir)
    if not os.path.isdir(ws_abs):
        return []

    if registry is None:
        from .process_registry import get_process_registry
        registry = get_process_registry()

    active_runs_by_path: Dict[str, int] = {}
    active_pids_by_path: Dict[str, List[int]] = {}
    all_procs = (
        registry.list_all_processes(workspace_dir=ws_abs)
        if hasattr(registry, "list_all_processes")
        else registry.list_runs()
    )
    for run in all_procs:
        if run.get("status") == "running":
            raw_rpath = run.get("path", "") or run.get("cwd", "")
            if not raw_rpath:
                continue
            norm_p = os.path.normcase(os.path.abspath(raw_rpath))
            active_runs_by_path[norm_p] = active_runs_by_path.get(norm_p, 0) + 1
            if run.get("pid"):
                active_pids_by_path.setdefault(norm_p, []).append(int(run["pid"]))

    entries: List[Dict[str, Any]] = []
    for name in sorted(os.listdir(ws_abs), key=lambda n: n.lower()):
        if name in _IGNORED_DIRS or name.startswith(".") or name == "_sandbox":
            continue
        full = os.path.join(ws_abs, name)
        try:
            mtime = os.path.getmtime(full)
        except OSError:
            mtime = 0.0

        if os.path.isdir(full):
            all_files: List[str] = []
            runnable: List[str] = []
            tests: List[str] = []
            for r_dir, dnames, fnames in os.walk(full):
                dnames[:] = sorted(d for d in dnames if d not in _IGNORED_DIRS and not d.startswith("."))
                for f in sorted(fnames):
                    fpath = os.path.join(r_dir, f)
                    all_files.append(fpath)
                    ext = os.path.splitext(f)[1].lower()
                    if is_test_filename(f):
                        tests.append(fpath)
                    elif ext in _RUNNABLE_EXTS and f != "__init__.py":
                        runnable.append(fpath)

            entry_point = None
            if runnable:
                by_name = {os.path.basename(p).lower(): p for p in runnable}
                for candidate_name in _ENTRY_PRIORITY:
                    if candidate_name in by_name:
                        entry_point = by_name[candidate_name]
                        break
                if not entry_point:
                    entry_point = runnable[0]

            proj_norm = os.path.normcase(os.path.abspath(full))
            active_pids: List[int] = list(active_pids_by_path.get(proj_norm, []))
            for p_str, pid_list in active_pids_by_path.items():
                if p_str != proj_norm and (p_str.startswith(proj_norm + os.sep) or p_str in {os.path.normcase(x) for x in all_files}):
                    for _pid in pid_list:
                        if _pid not in active_pids:
                            active_pids.append(_pid)
            active_count = len(active_pids) if active_pids else sum(active_runs_by_path.get(os.path.normcase(p), 0) for p in runnable)
            entries.append({
                "kind": "project",
                "name": name,
                "path": full,
                "rel_path": name,
                "modified_at": mtime,
                "file_count": len(all_files),
                "entry_point": entry_point,
                "entry_name": os.path.basename(entry_point) if entry_point else "",
                "has_tests": bool(tests),
                "test_count": len(tests),
                "active_runs": active_count,
                "active_pids": active_pids,
                "files": [
                    {
                        "name": os.path.relpath(p, full).replace("\\", "/"),
                        "path": p,
                        "is_test": is_test_filename(p),
                        "runnable": os.path.splitext(p)[1].lower() in _RUNNABLE_EXTS,
                    }
                    for p in sorted(all_files)[:50]
                ],
            })
        elif os.path.isfile(full):
            ext = os.path.splitext(name)[1].lower()
            if ext in _RUNNABLE_EXTS or ext in {".html", ".htm", ".json", ".yaml", ".yml", ".md"}:
                companion_tests, _ = find_project_tests(full, ws_abs)
                entries.append({
                    "kind": "file",
                    "name": name,
                    "path": full,
                    "rel_path": name,
                    "ext": ext.lstrip("."),
                    "modified_at": mtime,
                    "entry_point": full if ext in _RUNNABLE_EXTS else None,
                    "entry_name": name if ext in _RUNNABLE_EXTS else "",
                    "has_tests": bool(companion_tests),
                    "test_count": len(companion_tests),
                    "active_runs": active_runs_by_path.get(os.path.normcase(full), 0),
                    "files": [],
                })

    entries.sort(key=lambda e: e.get("modified_at", 0.0), reverse=True)
    return entries
