"""
hecos/modules/executor/process_watchdog.py
Persisted PID tracking, orphaned OS workspace process discovery, safe process-tree
termination, and lock-safe project/file deletion (especially on Windows).
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Set

try:
    import psutil
except ImportError:  # pragma: no cover
    psutil = None  # type: ignore

from .file_manager import logger

_PID_FILE_LOCK = threading.Lock()


def _resolve_pid_store_path() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    hecos_pkg = os.path.abspath(os.path.join(here, "..", ".."))
    run_dir = os.path.join(hecos_pkg, "data", "run")
    os.makedirs(run_dir, exist_ok=True)
    return os.path.join(run_dir, "workspace_pids.json")


def _load_pid_map(store_path: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    path = store_path or _resolve_pid_store_path()
    with _PID_FILE_LOCK:
        if not os.path.isfile(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}


def _save_pid_map(data: Dict[str, Dict[str, Any]], store_path: Optional[str] = None) -> None:
    path = store_path or _resolve_pid_store_path()
    with _PID_FILE_LOCK:
        tmp = f"{path}.tmp.{os.getpid()}.{threading.get_ident()}"
        try:
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(data, fh, ensure_ascii=False, indent=2)
            os.replace(tmp, path)
        except OSError as exc:
            logger.debug(f"[WATCHDOG] Failed saving workspace PID store: {exc}")


def record_started_pid(
    *,
    run_id: str,
    pid: int,
    target_path: str,
    cwd: str,
    name: str,
    command: str,
    started_at: float,
    store_path: Optional[str] = None,
) -> None:
    """Persist metadata for a spawned workspace child process across restarts."""
    if not run_id or not pid:
        return
    data = _load_pid_map(store_path=store_path)
    # Prune dead PIDs opportunistically
    if psutil is not None:
        data = {
            k: v for k, v in data.items()
            if isinstance(v, dict) and v.get("pid") and psutil.pid_exists(int(v["pid"]))
        }
    data[str(run_id)] = {
        "run_id": str(run_id),
        "pid": int(pid),
        "path": os.path.abspath(target_path) if target_path else "",
        "cwd": os.path.abspath(cwd) if cwd else "",
        "name": str(name or ""),
        "command": str(command or ""),
        "started_at": float(started_at or time.time()),
    }
    _save_pid_map(data, store_path=store_path)


def unrecord_pid(run_id: Optional[str] = None, *, pid: Optional[int] = None, store_path: Optional[str] = None) -> None:
    """Remove an exited or stopped process record from the persistent PID store."""
    data = _load_pid_map(store_path=store_path)
    changed = False
    if run_id and str(run_id) in data:
        data.pop(str(run_id), None)
        changed = True
    if pid is not None:
        doomed = [k for k, v in data.items() if isinstance(v, dict) and int(v.get("pid") or -1) == int(pid)]
        for k in doomed:
            data.pop(k, None)
            changed = True
    if changed:
        _save_pid_map(data, store_path=store_path)


def _is_path_within(candidate: str, parent: str) -> bool:
    """Return True if candidate path equals or is strictly inside parent directory."""
    if not candidate or not parent:
        return False
    try:
        cand_abs = os.path.normcase(os.path.abspath(candidate))
        parent_abs = os.path.normcase(os.path.abspath(parent))
        if cand_abs == parent_abs:
            return True
        return os.path.commonpath([cand_abs, parent_abs]) == parent_abs
    except Exception:
        return False


_PROTECTED_SYSTEM_BINARIES: Set[str] = {
    "system",
    "registry",
    "smss.exe",
    "csrss.exe",
    "wininit.exe",
    "services.exe",
    "lsass.exe",
    "svchost.exe",
    "winlogon.exe",
    "fontdrvhost.exe",
    "dwm.exe",
    "explorer.exe",
    "conhost.exe",
    "windowsterminal.exe",
    "openconsole.exe",
    "searchindexer.exe",
    "searchprotocolhost.exe",
    "msmpeng.exe",
    "securityhealthservice.exe",
    "onedrive.exe",
    "onedrive.sync.service.exe",
    "filecoauth.exe",
    "code.exe",
    "cursor.exe",
    "antigravity.exe",
    "antigravity ide.exe",
    "pyrefly.exe",
    "wsl.exe",
    "wslservice.exe",
}


def _is_protected_system_process(proc_name: str) -> bool:
    low = (proc_name or "").strip().lower()
    if not low:
        return False
    if low in _PROTECTED_SYSTEM_BINARIES:
        return True
    return low.startswith(("onedrive", "antigravity", "msmpeng"))


def _protected_ancestor_pids() -> Set[int]:
    """Return PIDs that must never be killed (current process and its parent chain)."""
    protected: Set[int] = {os.getpid()}
    if psutil is not None:
        try:
            me = psutil.Process(os.getpid())
            for parent in me.parents():
                protected.add(parent.pid)
        except Exception:
            pass
    return protected


def _extract_matching_target_from_tokens(cmdline: List[str], scope_dir: str) -> str:
    """Find the most specific absolute script/path token inside `cmdline` within `scope_dir`."""
    candidates: List[str] = []
    for raw_tok in cmdline or []:
        if not raw_tok:
            continue
        for sub in str(raw_tok).split(os.pathsep):
            clean = sub.strip().strip('"').strip("'")
            if not clean or len(clean) < 3 or clean.startswith("-"):
                continue
            if not os.path.isabs(clean):
                continue
            if _is_path_within(clean, scope_dir):
                candidates.append(os.path.abspath(clean))
    if not candidates:
        return ""
    # Prefer actual file path (longer / deeper) over folder root
    candidates.sort(key=lambda p: (0 if os.path.isfile(p) else 1, -len(p)))
    return candidates[0]


def _resolve_project_name(matched_path: str, workspace_dir: str) -> str:
    if not matched_path:
        return "workspace"
    if workspace_dir and _is_path_within(matched_path, workspace_dir):
        try:
            rel = os.path.relpath(os.path.abspath(matched_path), os.path.abspath(workspace_dir))
            first = rel.split(os.sep)[0]
            if first and first != ".":
                return first
        except Exception:
            pass
    return os.path.basename(matched_path.rstrip("\\/")) or "workspace"


def discover_workspace_processes(
    *,
    workspace_dir: Optional[str] = None,
    target_path: Optional[str] = None,
    scan_open_files: bool = False,
    store_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Discover live OS processes operating inside `target_path` or `workspace_dir`,
    including orphaned processes surviving previous Hecos restarts.
    """
    scope_dir = os.path.abspath(target_path or workspace_dir or "")
    if not scope_dir or psutil is None:
        return []

    scope_is_dir = not os.path.isfile(scope_dir)
    ws_root = os.path.abspath(workspace_dir) if workspace_dir else scope_dir
    protected = _protected_ancestor_pids()
    recorded_by_pid: Dict[int, Dict[str, Any]] = {}
    for rec in _load_pid_map(store_path=store_path).values():
        if isinstance(rec, dict) and rec.get("pid"):
            recorded_by_pid[int(rec["pid"])] = rec

    found: List[Dict[str, Any]] = []
    seen_pids: Set[int] = set()

    for proc in psutil.process_iter(["pid", "ppid", "name", "cmdline", "create_time"]):
        try:
            pid = int(proc.info.get("pid") or 0)
            if pid <= 0 or pid in protected or pid in seen_pids:
                continue

            proc_name = str(proc.info.get("name") or "")
            if pid not in recorded_by_pid and _is_protected_system_process(proc_name):
                continue

            cmdline = [str(x) for x in (proc.info.get("cmdline") or []) if x]
            matched_path = _extract_matching_target_from_tokens(cmdline, scope_dir)

            if not matched_path and pid in recorded_by_pid:
                rec_path = str(recorded_by_pid[pid].get("path") or "")
                rec_cwd = str(recorded_by_pid[pid].get("cwd") or "")
                if rec_path and _is_path_within(rec_path, scope_dir):
                    matched_path = rec_path
                elif scope_is_dir and rec_cwd and _is_path_within(rec_cwd, scope_dir):
                    matched_path = rec_cwd

            proc_cwd = ""
            if not matched_path and scope_is_dir:
                try:
                    proc_cwd = proc.cwd() or ""
                    if proc_cwd and _is_path_within(proc_cwd, scope_dir):
                        matched_path = proc_cwd
                except Exception:
                    proc_cwd = ""

            if not matched_path and scan_open_files:
                try:
                    for of in proc.open_files():
                        if of.path and _is_path_within(of.path, scope_dir):
                            matched_path = of.path
                            break
                except Exception:
                    pass

            if not matched_path:
                continue

            if not proc_cwd:
                try:
                    proc_cwd = proc.cwd() or ""
                except Exception:
                    proc_cwd = os.path.dirname(matched_path) if os.path.isfile(matched_path) else matched_path

            seen_pids.add(pid)
            rec_meta = recorded_by_pid.get(pid, {})
            display_cmd = rec_meta.get("command") or " ".join(cmdline[:6])
            found.append({
                "pid": pid,
                "ppid": int(proc.info.get("ppid") or 0),
                "process_name": str(proc.info.get("name") or ""),
                "name": rec_meta.get("name") or os.path.basename(matched_path) or str(proc.info.get("name") or ""),
                "project_name": _resolve_project_name(matched_path, ws_root),
                "path": os.path.abspath(matched_path),
                "cwd": os.path.abspath(proc_cwd) if proc_cwd else "",
                "command": display_cmd[:260],
                "started_at": float(rec_meta.get("started_at") or proc.info.get("create_time") or time.time()),
                "recorded_run_id": rec_meta.get("run_id") or "",
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
        except Exception:
            continue

    return found


def terminate_pid_tree(pid: int, timeout: float = 2.0) -> bool:
    """Terminate a process and all its child processes reliably across Windows/POSIX."""
    if not pid or pid in _protected_ancestor_pids():
        return False

    if psutil is None:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                capture_output=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            return True
        return False

    try:
        parent = psutil.Process(int(pid))
    except psutil.NoSuchProcess:
        unrecord_pid(pid=pid)
        return True
    except Exception:
        return False

    try:
        children = parent.children(recursive=True)
    except Exception:
        children = []
    targets = children + [parent]

    for p in targets:
        try:
            p.terminate()
        except Exception:
            pass

    _, alive = psutil.wait_procs(targets, timeout=max(0.2, min(timeout, 5.0)))
    for p in alive:
        try:
            p.kill()
        except Exception:
            pass

    if os.name == "nt" and psutil.pid_exists(int(pid)):
        try:
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                capture_output=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        except Exception:
            pass

    # Brief poll for handle release on Windows
    deadline = time.monotonic() + 1.5
    while psutil.pid_exists(int(pid)) and time.monotonic() < deadline:
        time.sleep(0.05)

    still_up = psutil.pid_exists(int(pid))
    if not still_up:
        unrecord_pid(pid=pid)
    return not still_up


def stop_processes_for_path(
    target_path: str,
    *,
    registry: Any = None,
    workspace_dir: Optional[str] = None,
    scan_open_files: bool = False,
) -> Dict[str, Any]:
    """
    Stop both managed Hecos runs and orphaned OS processes locking or running `target_path`.
    """
    abs_target = os.path.abspath(target_path)
    target_is_dir = not os.path.isfile(abs_target)
    stopped_pids: List[int] = []
    stopped_run_ids: List[str] = []

    # 1. Stop matching tracked ManagedProcessRegistry entries first
    if registry is not None:
        for run in registry.list_runs():
            if run.get("status") != "running":
                continue
            r_path = str(run.get("path") or "")
            r_cwd = str(run.get("cwd") or "")
            if (r_path and _is_path_within(r_path, abs_target)) or (
                target_is_dir and r_cwd and _is_path_within(r_cwd, abs_target)
            ):
                rid = str(run.get("run_id") or "")
                res = registry.stop_run(rid)
                if res.get("ok"):
                    stopped_run_ids.append(rid)
                    if run.get("pid"):
                        stopped_pids.append(int(run["pid"]))

    # 2. Discover & terminate any orphaned/child OS processes running inside target_path
    os_procs = discover_workspace_processes(
        workspace_dir=workspace_dir or abs_target,
        target_path=abs_target,
        scan_open_files=scan_open_files,
    )
    for proc_info in os_procs:
        pid = int(proc_info["pid"])
        if pid in stopped_pids:
            continue
        if terminate_pid_tree(pid):
            stopped_pids.append(pid)
            logger.info(
                f"[WATCHDOG] Stopped OS process PID={pid} ({proc_info.get('name')}) locking {abs_target}"
            )

    if stopped_pids:
        time.sleep(0.15)  # Allow Windows filesystem handle table to drain cleanly

    return {
        "ok": True,
        "target": abs_target,
        "stopped_pids": stopped_pids,
        "stopped_run_ids": stopped_run_ids,
        "stopped_count": len(stopped_pids),
    }


def _force_remove_readonly(func: Callable[..., Any], path: str, _exc_info: Any) -> None:
    """Handle read-only files (such as `.git` objects on Windows) during rmtree."""
    try:
        os.chmod(path, stat.S_IWRITE)
    except OSError:
        pass
    func(path)


def safe_remove_path(
    target_path: str,
    *,
    registry: Any = None,
    workspace_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Safely delete a file or folder inside workspace/Drive:
    - Stops any tracked or orphaned processes locking `target_path` first.
    - Clears Windows read-only attributes (e.g. `.git` objects).
    - Retries cleanly if Windows briefly holds file handles after termination.
    """
    abs_target = os.path.abspath(target_path)
    if not os.path.exists(abs_target):
        return {"ok": False, "error": "Path not found.", "stopped_pids": []}

    ws_root = os.path.abspath(workspace_dir) if workspace_dir else ""
    inside_workspace = bool(ws_root and _is_path_within(abs_target, ws_root))

    stopped_pids: List[int] = []
    if inside_workspace:
        pre = stop_processes_for_path(abs_target, registry=registry, workspace_dir=ws_root)
        stopped_pids.extend(pre.get("stopped_pids") or [])

    last_err: Optional[Exception] = None
    for attempt in range(4):
        try:
            if os.path.isdir(abs_target):
                shutil.rmtree(abs_target, onerror=_force_remove_readonly)
            else:
                try:
                    os.chmod(abs_target, stat.S_IWRITE)
                except OSError:
                    pass
                os.remove(abs_target)
            return {"ok": True, "path": abs_target, "stopped_pids": stopped_pids}
        except (PermissionError, OSError) as exc:
            last_err = exc
            # On lock error (e.g. WinError 32), escalate to open-file handle scan across OS processes
            unlock = stop_processes_for_path(
                abs_target,
                registry=registry,
                workspace_dir=ws_root or abs_target,
                scan_open_files=True,
            )
            for pid in unlock.get("stopped_pids") or []:
                if pid not in stopped_pids:
                    stopped_pids.append(pid)
            time.sleep(0.15 * (attempt + 1))

    return {
        "ok": False,
        "error": str(last_err or "Failed to delete locked path."),
        "stopped_pids": stopped_pids,
    }
