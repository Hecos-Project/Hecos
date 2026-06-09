import os
import sys
import subprocess
import time
import threading

from hecos.tray.config import _ROOT
from hecos.tray.utils import is_hecos_online

# Hold a reference to the subprocess so we can terminate it later
_hecos_process = None

def get_platform_python():
    """Returns the correct python executable depending on the environment."""
    # If running from a venv, sys.executable points to the venv python
    return sys.executable

def _wait_and_respawn(proc):
    """Waits for the subprocess to finish. If exit code is 42, respawns it."""
    proc.wait()
    # If returned 42, it means the Web UI requested a reboot
    if getattr(proc, 'returncode', None) == 42:
        print("[ORCHESTRATOR] Hecos requested reboot (Exit 42). Respawning...")
        
        # Wait up to 5 seconds for the port to release
        for _ in range(10):
            if not is_hecos_online():
                break
            time.sleep(0.5)
            
        # If it's still online (ghost process or TIME_WAIT), forcefully kill by port
        if is_hecos_online():
            print("[ORCHESTRATOR] Port still held after Exit 42, forcing kill...")
            _kill_by_port()
            time.sleep(1)
            
        start_hecos()


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
        boot_log_path = os.path.join(_ROOT, "hecos", "logs", "hecos_boot_trace.log")
        boot_log = open(boot_log_path, "a", encoding="utf-8")
        # Add a visual separator for new boot attempts
        boot_log.write(f"\n{'='*50}\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] ORCHESTRATOR: Spawning Hecos backend...\n{'='*50}\n")
        boot_log.flush()

        if sys.platform == "win32":
            # creationflags=0x08000000 means CREATE_NO_WINDOW (runs silently in background)
            _hecos_process = subprocess.Popen(
                [python_exe, "-m", "hecos.modules.web_ui.server", "--no-gui"],
                cwd=_ROOT,
                stdout=boot_log,
                stderr=subprocess.STDOUT,
                creationflags=0x08000000
            )
        else:
            # On Linux/Mac, just run it cleanly in the background
            _hecos_process = subprocess.Popen(
                [python_exe, "-m", "hecos.modules.web_ui.server", "--no-gui"],
                cwd=_ROOT,
                stdout=boot_log,
                stderr=subprocess.STDOUT
            )
        
        # Start a monitor thread to handle automatic reboots (exit code 42)
        threading.Thread(target=_wait_and_respawn, args=(_hecos_process,), daemon=True).start()
        
        print("[ORCHESTRATOR] Hecos background process spawned successfully.")
    except Exception as e:
        print(f"[ORCHESTRATOR] Failed to spawn Hecos: {e}")

def stop_hecos():
    """Terminates the background Hecos subprocess."""
    global _hecos_process
    if _hecos_process is not None:
        try:
            _hecos_process.terminate()
            _hecos_process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            _hecos_process.kill()
        except Exception:
            pass
        _hecos_process = None
        print("[ORCHESTRATOR] Hecos process stopped.")
    else:
        # Tray was restarted while Hecos was already running — kill by port
        _kill_by_port()


def _kill_by_port():
    """Find and kill whichever process is holding HECOS_PORT."""
    from hecos.tray.config import HECOS_PORT
    try:
        import psutil
        killed = False
        for conn in psutil.net_connections(kind="tcp"):
            if conn.laddr.port == HECOS_PORT and conn.status == "LISTEN":
                try:
                    proc = psutil.Process(conn.pid)
                    proc.terminate()
                    proc.wait(timeout=3)
                    killed = True
                    print(f"[ORCHESTRATOR] Killed process {conn.pid} on port {HECOS_PORT}.")
                except Exception as e:
                    print(f"[ORCHESTRATOR] Could not terminate PID {conn.pid}: {e}")
        if not killed:
            print(f"[ORCHESTRATOR] No process found on port {HECOS_PORT}.")
    except ImportError:
        print("[ORCHESTRATOR] psutil not available — cannot kill by port.")
    except Exception as e:
        print(f"[ORCHESTRATOR] _kill_by_port error: {e}")


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
    
    # Wait up to 5 seconds for the port to release
    for _ in range(10):
        if not is_hecos_online():
            break
        time.sleep(0.5)
        
    if is_hecos_online():
        print("[ORCHESTRATOR] Port still held after stop_hecos, forcing kill...")
        _kill_by_port()
        time.sleep(1)
        
    start_hecos()

