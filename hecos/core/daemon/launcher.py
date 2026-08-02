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


def get_main_script() -> str:
    """Returns the absolute path to the Hecos main entry point."""
    return os.path.join(PROJECT_ROOT, "main.py")


def spawn_hecos() -> subprocess.Popen:
    """
    Launches the Hecos main process as a subprocess.
    Sets HECOS_MONITORED_PROCESS=1 so main.py knows it is running under a Supervisor.
    Returns the Popen handle.
    """
    env = os.environ.copy()
    env["HECOS_MONITORED_PROCESS"] = "1"

    return subprocess.Popen(
        [sys.executable, get_main_script()],
        cwd=PROJECT_ROOT,
        env=env
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
