import os
import sys
import subprocess
import time

from hecos.tray.config import _ROOT
from hecos.tray.utils import is_hecos_online

# Hold a reference to the subprocess so we can terminate it later
_hecos_process = None

def get_platform_python():
    """Returns the correct python executable depending on the environment."""
    # If running from a venv, sys.executable points to the venv python
    return sys.executable

def start_hecos():
    """
    Spawns the Hecos system as a background subprocess of the Tray App.
    """
    global _hecos_process
    if is_hecos_running():
        return  # Already running

    server_script = os.path.join(_ROOT, "hecos", "modules", "web_ui", "server.py")
    if not os.path.exists(server_script):
        print(f"[ORCHESTRATOR] Error: Could not find {server_script}")
        return

    python_exe = get_platform_python()
    
    try:
        if sys.platform == "win32":
            # creationflags=0x08000000 means CREATE_NO_WINDOW (runs silently in background)
            _hecos_process = subprocess.Popen(
                [python_exe, "-m", "hecos.modules.web_ui.server", "--no-gui"],
                cwd=_ROOT,
                creationflags=0x08000000
            )
        else:
            # On Linux/Mac, just run it cleanly in the background
            _hecos_process = subprocess.Popen(
                [python_exe, "-m", "hecos.modules.web_ui.server", "--no-gui"],
                cwd=_ROOT,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        print("[ORCHESTRATOR] Hecos background process spawned successfully.")
    except Exception as e:
        print(f"[ORCHESTRATOR] Failed to spawn Hecos: {e}")

def stop_hecos():
    """Terminates the background Hecos subprocess."""
    global _hecos_process
    if _hecos_process is not None:
        try:
            # Send SIGTERM
            _hecos_process.terminate()
            # Wait up to 3 seconds for graceful shutdown
            _hecos_process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            # Force kill if it didn't terminate
            _hecos_process.kill()
        except Exception:
            pass
        _hecos_process = None
        print("[ORCHESTRATOR] Hecos process stopped.")
    else:
        # If the Tray was restarted but Hecos was kept alive (detached),
        # we can't kill it by object reference. In extreme cases, one might want
        # to kill by port (7070) here, but for now we rely on proper lifecycle pairing.
        pass

def is_hecos_running() -> bool:
    """
    Returns True if we see the process handle is alive, OR if the port is responding.
    (If the Tray app crashed and was restarted, _hecos_process might be None but is_hecos_online() will be True).
    """
    global _hecos_process
    
    # Fast reliable check if we started it
    if _hecos_process is not None:
        if _hecos_process.poll() is None:
            return True
        else:
            # Process died
            _hecos_process = None
            
    # Fallback: check if the port is bound
    return is_hecos_online()

def restart_hecos():
    """Stops the existing process and spawns a new one."""
    stop_hecos()
    time.sleep(1) # Give port time to release
    start_hecos()
