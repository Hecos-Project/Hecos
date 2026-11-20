"""
MODULE: TTS Process Registry & Lifecycle Guard
DESCRIPTION: Tracks spawned TTS daemon subprocesses (Piper IPC, Fish Speech Server),
             binds them to a Windows Job Object (KILL_ON_JOB_CLOSE) so no orphan
             processes survive os._exit(42) or crashes, reaps stale processes on boot,
             and manages the loopback-only local control token for Hecos-Tray.
"""

import os
import sys
import json
import time
import hmac
import secrets
import threading
import subprocess
from typing import Optional

from hecos.core.logging import logger

DEFAULT_FISH_PORT = 18480
DEFAULT_FISH_URL = f"http://127.0.0.1:{DEFAULT_FISH_PORT}/v1/tts"
LEGACY_FISH_URLS = {
    "http://127.0.0.1:8080/v1/tts",
    "http://localhost:8080/v1/tts",
    "http://127.0.0.1:8080",
    "http://localhost:8080",
}

_registry_lock = threading.Lock()
_job_lock = threading.Lock()
_job_handle = None
_job_init_attempted = False

_token_lock = threading.Lock()
_local_control_token: Optional[str] = None


def get_project_root() -> str:
    current_file = os.path.abspath(__file__)
    return os.path.abspath(os.path.join(current_file, "..", "..", "..", "..", ".."))


def _get_run_dir() -> str:
    run_dir = os.path.join(get_project_root(), "hecos", "data", "run")
    os.makedirs(run_dir, exist_ok=True)
    return run_dir


def get_registry_path() -> str:
    return os.path.join(_get_run_dir(), "tts_processes.json")


def get_control_token_path() -> str:
    return os.path.join(_get_run_dir(), "tts_control.json")


# ── Windows Job Object (Kernel-level orphan prevention) ───────────────────────

def _ensure_windows_job_object():
    """Creates a Windows Job Object configured with KILL_ON_JOB_CLOSE."""
    global _job_handle, _job_init_attempted
    if sys.platform != "win32":
        return None
    if _job_init_attempted:
        return _job_handle

    with _job_lock:
        if _job_init_attempted:
            return _job_handle
        _job_init_attempted = True
        try:
            import ctypes
            from ctypes import wintypes

            class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
                _fields_ = [
                    ("PerProcessUserTimeLimit", ctypes.c_int64),
                    ("PerJobUserTimeLimit", ctypes.c_int64),
                    ("LimitFlags", wintypes.DWORD),
                    ("MinimumWorkingSetSize", ctypes.c_size_t),
                    ("MaximumWorkingSetSize", ctypes.c_size_t),
                    ("ActiveProcessLimit", wintypes.DWORD),
                    ("Affinity", ctypes.c_size_t),
                    ("PriorityClass", wintypes.DWORD),
                    ("SchedulingClass", wintypes.DWORD),
                ]

            class IO_COUNTERS(ctypes.Structure):
                _fields_ = [
                    ("ReadOperationCount", ctypes.c_uint64),
                    ("WriteOperationCount", ctypes.c_uint64),
                    ("OtherOperationCount", ctypes.c_uint64),
                    ("ReadTransferCount", ctypes.c_uint64),
                    ("WriteTransferCount", ctypes.c_uint64),
                    ("OtherTransferCount", ctypes.c_uint64),
                ]

            class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
                _fields_ = [
                    ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
                    ("IoInfo", IO_COUNTERS),
                    ("ProcessMemoryLimit", ctypes.c_size_t),
                    ("JobMemoryLimit", ctypes.c_size_t),
                    ("PeakProcessMemoryUsed", ctypes.c_size_t),
                    ("PeakJobMemoryUsed", ctypes.c_size_t),
                ]

            kernel32 = ctypes.windll.kernel32
            kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
            kernel32.CreateJobObjectW.restype = ctypes.c_void_p
            kernel32.SetInformationJobObject.argtypes = [
                ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD
            ]
            kernel32.SetInformationJobObject.restype = wintypes.BOOL
            kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
            kernel32.CloseHandle.restype = wintypes.BOOL

            job = kernel32.CreateJobObjectW(None, None)
            if not job:
                return None

            info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
            # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
            # JOB_OBJECT_LIMIT_BREAKAWAY_OK      = 0x00000800
            info.BasicLimitInformation.LimitFlags = 0x00002000 | 0x00000800

            # JobObjectExtendedLimitInformation = 9
            ok = kernel32.SetInformationJobObject(
                job, 9, ctypes.byref(info), ctypes.sizeof(info)
            )
            if not ok:
                kernel32.CloseHandle(job)
                return None

            _job_handle = job
            return _job_handle
        except Exception as exc:
            logger.debug("TTS_REGISTRY", f"Job Object initialization skipped: {exc}")
            return None


def assign_to_job_object(pid: int) -> bool:
    """Binds a child PID to the current process's Job Object on Windows."""
    if sys.platform != "win32" or not pid:
        return False
    job = _ensure_windows_job_object()
    if not job:
        return False
    try:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.windll.kernel32
        kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel32.OpenProcess.restype = ctypes.c_void_p
        kernel32.AssignProcessToJobObject.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
        kernel32.CloseHandle.restype = wintypes.BOOL

        # PROCESS_SET_QUOTA (0x0100) | PROCESS_TERMINATE (0x0001)
        h_proc = kernel32.OpenProcess(0x0101, False, int(pid))
        if not h_proc:
            return False
        try:
            return bool(kernel32.AssignProcessToJobObject(job, h_proc))
        finally:
            kernel32.CloseHandle(h_proc)
    except Exception as exc:
        logger.debug("TTS_REGISTRY", f"Could not assign PID {pid} to Job Object: {exc}")
        return False


# ── PID Registry & Orphan Reaper ──────────────────────────────────────────────

def _read_registry_unlocked() -> dict:
    path = get_registry_path()
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write_registry_unlocked(data: dict) -> None:
    path = get_registry_path()
    tmp_path = path + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, path)
    except Exception as exc:
        logger.debug("TTS_REGISTRY", f"Failed writing TTS registry: {exc}")


def register_tts_process(engine: str, pid: int, name: str = "", port: Optional[int] = None) -> None:
    """Records a spawned TTS daemon process and binds it to the Windows Job Object."""
    if not pid:
        return
    assign_to_job_object(pid)
    with _registry_lock:
        reg = _read_registry_unlocked()
        reg[engine] = {
            "pid": int(pid),
            "name": name,
            "port": port,
            "parent_pid": os.getpid(),
            "started_at": round(time.time(), 2),
        }
        _write_registry_unlocked(reg)


def unregister_tts_process(engine: str, pid: Optional[int] = None) -> None:
    """Removes a TTS daemon entry from the persistent registry."""
    with _registry_lock:
        reg = _read_registry_unlocked()
        entry = reg.get(engine)
        if entry and (pid is None or entry.get("pid") == pid):
            reg.pop(engine, None)
            _write_registry_unlocked(reg)


def _is_matching_tts_process(proc, engine: str) -> bool:
    """Verifies that a PID still belongs to the expected TTS engine before killing."""
    try:
        name = (proc.name() or "").lower()
        cmdline = " ".join(proc.cmdline() or []).lower()
    except Exception:
        return False

    if engine == "piper":
        return "piper" in name and "--json-input" in cmdline
    if engine in ("fish_speech", "fish"):
        return "fish_speech_server.py" in cmdline
    return False


def kill_process_tree_safe(pid: int) -> bool:
    """Terminates a process and all its children safely."""
    if not pid or pid == os.getpid():
        return False
    try:
        import psutil
        try:
            parent = psutil.Process(pid)
        except psutil.NoSuchProcess:
            return False

        try:
            children = parent.children(recursive=True)
        except Exception:
            children = []

        targets = [parent] + children
        for p in targets:
            try:
                p.terminate()
            except Exception:
                pass
        _, alive = psutil.wait_procs(targets, timeout=2.5)
        for p in alive:
            try:
                p.kill()
            except Exception:
                pass
        if alive:
            psutil.wait_procs(alive, timeout=1.5)
        return True
    except ImportError:
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                capture_output=True,
                timeout=5,
                creationflags=0x08000000,
            )
            return True
    except Exception as exc:
        logger.debug("TTS_REGISTRY", f"kill_process_tree_safe({pid}) error: {exc}")
    return False


def reap_orphan_tts_processes(
    engine: Optional[str] = None,
    force_all: bool = False,
    include_own: bool = False,
) -> int:
    """
    Terminates stale/orphaned TTS daemon subprocesses (Piper --json-input, Fish Speech server).
    - `include_own=True`: also kills daemons spawned by `os.getpid()` (safe for process atexit
      without disturbing daemons owned by another live Hecos Core process).
    - `force_all=True`: kills all matching local TTS daemons regardless of parent (used for
      explicit user Stop / Stop-All actions and watchdog teardown).
    """
    reaped = 0
    my_pid = os.getpid()
    engines_to_check = [engine] if engine else ["piper", "fish_speech"]

    try:
        import psutil
    except ImportError:
        return 0

    # 1. Check PIDs recorded in registry
    with _registry_lock:
        reg = _read_registry_unlocked()
        changed = False
        for eng in list(reg.keys()):
            if engine and eng != engine:
                continue
            entry = reg.get(eng) or {}
            pid = entry.get("pid")
            parent_pid = entry.get("parent_pid")
            if not pid:
                reg.pop(eng, None)
                changed = True
                continue

            parent_alive = bool(parent_pid and psutil.pid_exists(parent_pid))
            should_reap = (
                force_all
                or (include_own and parent_pid == my_pid)
                or (parent_pid != my_pid and not parent_alive)
            )
            if should_reap:
                try:
                    proc = psutil.Process(pid)
                    if _is_matching_tts_process(proc, eng):
                        logger.info("TTS_REGISTRY", f"Reaping lingering {eng} daemon (PID {pid})...")
                        if kill_process_tree_safe(pid):
                            reaped += 1
                except psutil.NoSuchProcess:
                    pass
                except Exception:
                    pass
                reg.pop(eng, None)
                changed = True
        if changed:
            _write_registry_unlocked(reg)

    # 2. Scan live processes for unrecorded orphans or duplicate instances
    for proc in psutil.process_iter(["pid", "ppid", "name", "cmdline"]):
        try:
            pid = proc.info["pid"]
            if pid == my_pid:
                continue
            ppid = proc.info.get("ppid") or 0
            for eng in engines_to_check:
                if _is_matching_tts_process(proc, eng):
                    parent_alive = bool(ppid and psutil.pid_exists(ppid))
                    should_reap = (
                        force_all
                        or (include_own and ppid == my_pid)
                        or (ppid != my_pid and not parent_alive)
                    )
                    if should_reap:
                        logger.info("TTS_REGISTRY", f"Reaping orphaned {eng} process (PID {pid}, PPID {ppid})...")
                        if kill_process_tree_safe(pid):
                            reaped += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        except Exception:
            continue

    return reaped


# ── Local Loopback Control Token (Hecos-Tray <-> WebUI) ───────────────────────

def init_local_control_token(port: int = 7070, scheme: str = "http") -> str:
    """Generates or updates the per-boot local loopback token used by Hecos-Tray."""
    global _local_control_token
    with _token_lock:
        if not _local_control_token:
            _local_control_token = secrets.token_hex(32)
        payload = {
            "token": _local_control_token,
            "port": int(port),
            "scheme": scheme,
            "pid": os.getpid(),
            "updated_at": round(time.time(), 2),
        }
        path = get_control_token_path()
        tmp_path = path + ".tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            os.replace(tmp_path, path)
        except Exception as exc:
            logger.debug("TTS_REGISTRY", f"Could not write local control token: {exc}")
        return _local_control_token


def verify_local_control_token(candidate: str) -> bool:
    """Constant-time verification of the local loopback token."""
    if not candidate or not _local_control_token:
        return False
    try:
        return hmac.compare_digest(str(candidate), _local_control_token)
    except Exception:
        return False
