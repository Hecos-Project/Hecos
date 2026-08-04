"""
hecos/core/daemon/launcher.py
─────────────────────────────────────────────────────────────────────────────
Responsible for spawning and terminating the Hecos main process subprocess.
Isolated here so the watchdog loop stays clean and this module can later be
compiled (e.g. Cython / Nuitka) independently for performance and security.
─────────────────────────────────────────────────────────────────────────────
"""

import os
import sys
import subprocess

# Project root: hecos/core/daemon/ -> hecos/core/ -> hecos/ -> root
_THIS_DIR  = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.normpath(os.path.join(_THIS_DIR, "..", "..", ".."))

# Log where child stdout/stderr will be written
_BOOT_TRACE = os.path.join(PROJECT_ROOT, "hecos", "logs", "hecos_boot_trace.log")


def get_main_cmd(is_web: bool = False) -> list:
    """Returns the command list to launch Hecos (CLI or WebUI)."""
    # Ensure the child runs as hecos_main.exe, not whatever the daemon was called
    from hecos.core.system.process_naming import get_named_executable
    exe = get_named_executable("hecos_main")
    
    if is_web:
        # Use -m (module mode) so relative imports inside server.py work correctly.
        # Running server.py as a direct script would break 'from .routes import ...' etc.
        return [exe, "-m", "hecos.modules.web_ui.server", "--no-gui"]
    return [exe, os.path.join(PROJECT_ROOT, "main.py")]


def spawn_hecos(is_web: bool = False) -> subprocess.Popen:
    """
    Launches the Hecos main process as a subprocess.
    Sets HECOS_MONITORED_PROCESS=1 so the child knows it is running under a Supervisor.
    Redirects stdout+stderr to the boot trace log for visibility.
    Returns the Popen handle.
    """
    env = os.environ.copy()
    env["HECOS_MONITORED_PROCESS"] = "1"

    # Add project root to PYTHONPATH so the child can resolve 'hecos'
    env["PYTHONPATH"] = PROJECT_ROOT + os.pathsep + env.get("PYTHONPATH", "")

    os.makedirs(os.path.dirname(_BOOT_TRACE), exist_ok=True)
    boot_log = open(_BOOT_TRACE, "a", encoding="utf-8", errors="replace")

    cmd = get_main_cmd(is_web)
    print(f"[DAEMON LAUNCHER] Spawning: {' '.join(cmd)}", flush=True)

    return subprocess.Popen(
        cmd,
        cwd=PROJECT_ROOT,
        env=env,
        stdout=boot_log,
        stderr=boot_log,
    )


def terminate_process(process: subprocess.Popen) -> None:
    """Gracefully terminates a running Hecos process. Falls back to kill if needed."""
    if process and process.poll() is None:
        try:
            process.terminate()
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        except Exception:
            pass

