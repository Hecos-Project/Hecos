"""
hecos/modules/executor/process_runner.py
Unified one-shot script/test runner and managed background app process registry
for Hecos EXECUTOR and the WebUI Workspace Runner.
"""

from __future__ import annotations

import os
import re
import shlex
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field
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


_LOCAL_URL_RE = re.compile(
    r"https?://(?:127\.0\.0\.1|localhost|0\.0\.0\.0):\d{2,5}(?:/[^\s\"'<>)\]]*)?",
    re.IGNORECASE,
)
_HTTP_PORT_HINT_RE = re.compile(
    r"(?:on|port|listening on)\s+(?:0\.0\.0\.0|127\.0\.0\.1|localhost)?\s*(?:port\s+)?(\d{4,5})",
    re.IGNORECASE,
)
_RUNNABLE_EXTS = {".py", ".bat", ".cmd", ".sh"}
_ENTRY_PRIORITY = ("main.py", "app.py", "run.py", "server.py", "cli.py", "index.py")


def extract_local_urls(text: str) -> List[str]:
    """Extract unique localhost / 127.0.0.1 HTTP URLs from process output."""
    if not text:
        return []
    found: List[str] = []
    seen = set()
    for match in _LOCAL_URL_RE.finditer(text):
        url = match.group(0).rstrip(".,;:")
        url = url.replace("://0.0.0.0:", "://127.0.0.1:")
        if url not in seen:
            seen.add(url)
            found.append(url)
    if not found:
        for m in _HTTP_PORT_HINT_RE.finditer(text):
            port = int(m.group(1))
            if 1024 <= port <= 65535:
                url = f"http://127.0.0.1:{port}"
                if url not in seen:
                    seen.add(url)
                    found.append(url)
    return found


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
    clean = (target_path or "").strip()
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
        return None, f"Path not found: {candidate}"
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

    # When editing a standalone file in workspace root, match only companion tests for that stem.
    if os.path.normcase(target_dir) == os.path.normcase(ws_abs):
        stem = os.path.splitext(fname)[0]
        candidates = [
            os.path.join(ws_abs, f"test_{stem}.py"),
            os.path.join(ws_abs, f"{stem}_test.py"),
            os.path.join(ws_abs, "tests", f"test_{stem}.py"),
            os.path.join(ws_abs, "tests", f"{stem}_test.py"),
        ]
        return [p for p in candidates if os.path.isfile(p)], ws_abs

    # Inside a dedicated project subfolder, walk up once if inside package/src/tests to find project root.
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
    popen_flags = (subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)

    started = time.perf_counter()
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

        # Support bare `def test_*(): assert ...` scripts when unittest finds 0 TestCase tests
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


@dataclass
class ManagedRunEntry:
    run_id: str
    target_path: str
    name: str
    command_display: str
    cwd: str
    log_path: str
    started_at: float
    process: subprocess.Popen
    log_file_handle: Any = None
    ended_at: Optional[float] = None
    exit_code: Optional[int] = None
    stopped_by_user: bool = False
    detected_urls: List[str] = field(default_factory=list)


class ManagedProcessRegistry:
    """Thread-safe registry for running scripts and persistent workspace apps."""

    _MAX_HISTORY = 40

    def __init__(self):
        self._lock = threading.RLock()
        self._runs: Dict[str, ManagedRunEntry] = {}

    def _close_log_handle(self, entry: ManagedRunEntry):
        if entry.log_file_handle is not None:
            try:
                entry.log_file_handle.flush()
                entry.log_file_handle.close()
            except Exception:
                pass
            entry.log_file_handle = None

    def _refresh_entry(self, entry: ManagedRunEntry) -> str:
        code = entry.process.poll()
        if code is not None and entry.exit_code is None:
            entry.exit_code = code
            entry.ended_at = entry.ended_at or time.time()
            self._close_log_handle(entry)
        return "running" if entry.exit_code is None else ("stopped" if entry.stopped_by_user else "exited")

    def _read_log_text(self, log_path: str, offset: int = 0, max_bytes: int = 65536) -> tuple[str, int]:
        if not os.path.isfile(log_path):
            return "", 0
        try:
            file_size = os.path.getsize(log_path)
            safe_offset = max(0, min(int(offset), file_size))
            with open(log_path, "rb") as fb:
                fb.seek(safe_offset)
                chunk = fb.read(max_bytes)
                new_offset = fb.tell()
            return chunk.decode("utf-8", errors="replace"), new_offset
        except OSError:
            return "", offset

    def _prune_old_runs_locked(self):
        finished = [
            e for e in self._runs.values()
            if self._refresh_entry(e) != "running"
        ]
        if len(finished) <= self._MAX_HISTORY:
            return
        finished.sort(key=lambda e: e.started_at)
        for old in finished[: len(finished) - self._MAX_HISTORY]:
            self._runs.pop(old.run_id, None)
            try:
                if os.path.isfile(old.log_path):
                    os.remove(old.log_path)
            except OSError:
                pass

    def start_target(
        self,
        target_path: str,
        workspace_dir: str,
        sandbox_dir: str,
        *,
        args: str = "",
        wait_seconds: float = 1.5,
        strict_workspace_only: bool = True,
        require_stay_alive: bool = False,
    ) -> Dict[str, Any]:
        """
        Launch an authorized script or app in workspace_dir, logging output under sandbox_dir/runs.
        If the process completes within wait_seconds (and require_stay_alive is False),
        returns final one-shot result; otherwise returns live running metadata for polling/Stop.
        """
        abs_target, err = resolve_authorized_target(
            target_path, workspace_dir, strict_workspace_only=strict_workspace_only
        )
        if err:
            return {"ok": False, "status": "error", "error": err, "output": err}
        if not os.path.isfile(abs_target):
            msg = f"Target is not a runnable file: {abs_target}"
            return {"ok": False, "status": "error", "error": msg, "output": msg}

        try:
            extra_args = shlex.split(args.strip(), posix=(os.name != "nt")) if args and args.strip() else []
        except ValueError as exc:
            msg = f"Invalid arguments syntax: {exc}"
            return {"ok": False, "status": "error", "error": msg, "output": msg}

        cmd, work_dir, display_cmd, build_err = _build_script_invocation(abs_target, extra_args, workspace_dir)
        if build_err or not cmd:
            return {"ok": False, "status": "error", "error": build_err or "Invalid command", "output": build_err or ""}

        runs_dir = os.path.join(os.path.abspath(sandbox_dir), "runs")
        os.makedirs(runs_dir, exist_ok=True)
        run_id = f"run_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        log_path = os.path.join(runs_dir, f"{run_id}.log")

        ws_abs = os.path.abspath(workspace_dir)
        import_roots = [ws_abs, work_dir] if os.path.normcase(work_dir) != os.path.normcase(ws_abs) else [ws_abs]
        env = _build_subproc_env(import_roots)

        try:
            log_fh = open(log_path, "w", encoding="utf-8", errors="replace")
        except OSError as exc:
            msg = f"Unable to open run log '{log_path}': {exc}"
            return {"ok": False, "status": "error", "error": msg, "output": msg}

        creationflags = 0
        if os.name == "nt":
            # Allow GUI windows to appear cleanly if launched locally, while avoiding extra console popup when possible
            creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)

        try:
            proc = subprocess.Popen(
                cmd,
                cwd=work_dir,
                env=env,
                stdout=log_fh,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                text=True,
                creationflags=creationflags,
            )
        except Exception as exc:
            try:
                log_fh.close()
            except Exception:
                pass
            msg = f"Failed to start process: {exc}"
            return {"ok": False, "status": "error", "error": msg, "output": msg}

        entry = ManagedRunEntry(
            run_id=run_id,
            target_path=abs_target,
            name=os.path.basename(abs_target),
            command_display=display_cmd,
            cwd=work_dir,
            log_path=log_path,
            started_at=time.time(),
            process=proc,
            log_file_handle=log_fh,
        )

        with self._lock:
            self._prune_old_runs_locked()
            self._runs[run_id] = entry

        wait_cap = max(0.2, min(float(wait_seconds or 1.5), 10.0))
        deadline = time.monotonic() + wait_cap
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                break
            time.sleep(0.08)

        with self._lock:
            status = self._refresh_entry(entry)
            output_text, offset = self._read_log_text(entry.log_path, offset=0)
            entry.detected_urls = extract_local_urls(output_text)
            duration_ms = int(((entry.ended_at or time.time()) - entry.started_at) * 1000)

        if status != "running":
            ok = (entry.exit_code == 0)
            AgentTracer.emit_action("run_script", entry.name, f"exit={entry.exit_code} ({duration_ms}ms)")
            if require_stay_alive and not ok:
                return {
                    "ok": False,
                    "status": status,
                    "execution_type": "app",
                    "run_id": run_id,
                    "pid": proc.pid,
                    "path": abs_target,
                    "name": entry.name,
                    "cwd": work_dir,
                    "command": display_cmd,
                    "exit_code": entry.exit_code,
                    "duration_ms": duration_ms,
                    "offset": offset,
                    "output": output_text or f"(exited with code {entry.exit_code})",
                    "detected_urls": entry.detected_urls,
                    "log_path": log_path,
                    "error": f"App exited immediately with code {entry.exit_code}.",
                }
            return {
                "ok": ok,
                "status": status,
                "execution_type": "oneshot",
                "run_id": run_id,
                "pid": proc.pid,
                "path": abs_target,
                "name": entry.name,
                "cwd": work_dir,
                "command": display_cmd,
                "exit_code": entry.exit_code,
                "duration_ms": duration_ms,
                "offset": offset,
                "output": output_text or "(completed with no output)",
                "detected_urls": entry.detected_urls,
                "log_path": log_path,
            }

        # Still alive after initial wait: give servers a tiny window if no URL/output flushed yet
        if not entry.detected_urls and len(output_text) < 20:
            time.sleep(0.45)
            with self._lock:
                status = self._refresh_entry(entry)
                output_text, offset = self._read_log_text(entry.log_path, offset=0)
                entry.detected_urls = extract_local_urls(output_text)

        AgentTracer.emit_action("start_app", entry.name, f"PID {proc.pid} ({run_id})")
        return {
            "ok": True if status == "running" else (entry.exit_code == 0),
            "status": status,
            "execution_type": "app" if status == "running" else "oneshot",
            "run_id": run_id,
            "pid": proc.pid,
            "path": abs_target,
            "name": entry.name,
            "cwd": work_dir,
            "command": display_cmd,
            "exit_code": entry.exit_code,
            "duration_ms": int((time.time() - entry.started_at) * 1000),
            "offset": offset,
            "output": output_text,
            "detected_urls": entry.detected_urls,
            "log_path": log_path,
        }

    def get_logs(self, run_id: str, offset: int = 0, tail_lines: int = 0) -> Dict[str, Any]:
        with self._lock:
            entry = self._runs.get(run_id)
            if not entry:
                return {"ok": False, "error": f"Unknown run_id: {run_id}"}
            status = self._refresh_entry(entry)
            text, new_offset = self._read_log_text(entry.log_path, offset=offset)
            # Re-scan full log for URL detection when offset > 0 missed earlier chunk
            if text:
                full_text = text if offset == 0 else self._read_log_text(entry.log_path, offset=0)[0]
                entry.detected_urls = extract_local_urls(full_text)
            if tail_lines and tail_lines > 0 and text:
                lines = text.splitlines()
                text = "\n".join(lines[-tail_lines:])
            return {
                "ok": True,
                "run_id": entry.run_id,
                "name": entry.name,
                "path": entry.target_path,
                "pid": entry.process.pid,
                "status": status,
                "exit_code": entry.exit_code,
                "offset": new_offset,
                "chunk": text,
                "detected_urls": list(entry.detected_urls),
                "duration_ms": int(((entry.ended_at or time.time()) - entry.started_at) * 1000),
            }

    def stop_run(self, run_id: str) -> Dict[str, Any]:
        with self._lock:
            entry = self._runs.get(run_id)
            if not entry:
                return {"ok": False, "error": f"Unknown run_id: {run_id}"}
            status = self._refresh_entry(entry)
            if status != "running":
                return {
                    "ok": True,
                    "run_id": run_id,
                    "status": status,
                    "exit_code": entry.exit_code,
                    "message": "Process already finished.",
                }
            entry.stopped_by_user = True
            proc = entry.process

        # Perform OS termination outside lock to avoid blocking status reads
        try:
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                    capture_output=True,
                    timeout=5,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
            else:
                proc.terminate()
                try:
                    proc.wait(timeout=2.0)
                except subprocess.TimeoutExpired:
                    proc.kill()
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

        with self._lock:
            status = self._refresh_entry(entry)
            AgentTracer.emit_action("stop_app", entry.name, f"{run_id} ({status})")
            return {
                "ok": True,
                "run_id": run_id,
                "status": status,
                "exit_code": entry.exit_code,
                "message": f"Stopped {entry.name} (PID {proc.pid}).",
            }

    def list_runs(self) -> List[Dict[str, Any]]:
        with self._lock:
            items = []
            for entry in sorted(self._runs.values(), key=lambda e: e.started_at, reverse=True):
                status = self._refresh_entry(entry)
                if not entry.detected_urls:
                    full_text = self._read_log_text(entry.log_path, offset=0)[0]
                    entry.detected_urls = extract_local_urls(full_text)
                items.append({
                    "run_id": entry.run_id,
                    "name": entry.name,
                    "path": entry.target_path,
                    "command": entry.command_display,
                    "cwd": entry.cwd,
                    "pid": entry.process.pid,
                    "status": status,
                    "exit_code": entry.exit_code,
                    "started_at": entry.started_at,
                    "duration_ms": int(((entry.ended_at or time.time()) - entry.started_at) * 1000),
                    "detected_urls": list(entry.detected_urls),
                })
            return items


_REGISTRY = ManagedProcessRegistry()


def get_process_registry() -> ManagedProcessRegistry:
    """Return the global ManagedProcessRegistry singleton."""
    return _REGISTRY


def list_workspace_projects(workspace_dir: str) -> List[Dict[str, Any]]:
    """Catalog projects and runnable scripts in workspace_dir for the Workspace Runner UI."""
    ws_abs = os.path.abspath(workspace_dir)
    if not os.path.isdir(ws_abs):
        return []

    active_runs_by_path: Dict[str, int] = {}
    for run in _REGISTRY.list_runs():
        if run.get("status") == "running":
            norm_p = os.path.normcase(os.path.abspath(run.get("path", "")))
            active_runs_by_path[norm_p] = active_runs_by_path.get(norm_p, 0) + 1

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

            active_count = sum(active_runs_by_path.get(os.path.normcase(p), 0) for p in runnable)
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


def run_smart(
    target_path: str,
    mode: str = "auto",
    *,
    args: str = "",
    workspace_dir: str = "",
    sandbox_dir: str = "",
    timeout_seconds: int = 30,
    wait_seconds: float = 1.5,
    strict_workspace_only: bool = True,
) -> Dict[str, Any]:
    """Dispatch UI/API execution request to script, test, or managed persistent app runner."""
    clean_mode = (mode or "auto").strip().lower()
    if clean_mode == "test":
        return run_tests_for_target(
            target_path,
            workspace_dir,
            timeout_seconds=timeout_seconds,
            strict_workspace_only=strict_workspace_only,
        )
    if clean_mode == "app":
        return _REGISTRY.start_target(
            target_path,
            workspace_dir,
            sandbox_dir,
            args=args,
            wait_seconds=max(wait_seconds, 2.0),
            strict_workspace_only=strict_workspace_only,
            require_stay_alive=True,
        )
    return _REGISTRY.start_target(
        target_path,
        workspace_dir,
        sandbox_dir,
        args=args,
        wait_seconds=wait_seconds,
        strict_workspace_only=strict_workspace_only,
        require_stay_alive=False,
    )
