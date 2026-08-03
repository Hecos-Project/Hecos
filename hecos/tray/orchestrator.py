import os
import sys
import subprocess
import time
import threading

from hecos.tray.config import _ROOT
from hecos.tray.utils import is_hecos_online

# Hold a reference to the subprocess so we can terminate it later
_hecos_process = None
_daemon_process = None  # Separate reference when running under the Supervisor

def get_platform_python():
    """Returns the correct python executable depending on the environment."""
    if sys.platform == "win32":
        from hecos.core.system.process_naming import get_named_executable
        return get_named_executable("hecos_main")
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
        from hecos.tray.config import load_settings
        settings = load_settings()
        use_daemon = settings.get("use_daemon", False)

        boot_log_path = os.path.join(_ROOT, "hecos", "logs", "hecos_boot_trace.log")
        boot_log = open(boot_log_path, "a", encoding="utf-8")
        # Add a visual separator for new boot attempts
        boot_log.write(f"\n{'='*50}\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] ORCHESTRATOR: Spawning Hecos backend...\n{'='*50}\n")
        boot_log.flush()

        cmd = [python_exe]
        if use_daemon:
            cmd.extend(["-m", "hecos.core.daemon", "--web"])
            print("[ORCHESTRATOR] Spawning under new Watchdog Daemon...")
        else:
            cmd.extend(["-m", "hecos.modules.web_ui.server", "--no-gui"])
            print("[ORCHESTRATOR] Spawning standalone...")

        if sys.platform == "win32":
            # creationflags=0x08000000 means CREATE_NO_WINDOW (runs silently in background)
            _hecos_process = subprocess.Popen(
                cmd,
                cwd=_ROOT,
                stdout=boot_log,
                stderr=subprocess.STDOUT,
                creationflags=0x08000000
            )
        else:
            # On Linux/Mac, just run it cleanly in the background
            _hecos_process = subprocess.Popen(
                cmd,
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
    try:
        boot_log_path = os.path.join(_ROOT, "hecos", "logs", "hecos_boot_trace.log")
        with open(boot_log_path, "a", encoding="utf-8") as f:
            f.write(f"\n{'='*50}\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] 🔄 ORCHESTRATOR: RESTART TRIGGERED FROM TRAY\n{'='*50}\n")
    except Exception:
        pass

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


def start_hecos_with_daemon():
    """
    Spawns the Hecos Supervisor (hecos.core.daemon) as a background subprocess.
    Stops any existing standalone Hecos first to avoid port/lock conflicts.
    """
    global _daemon_process
    if is_daemon_running():
        print("[ORCHESTRATOR] Daemon is already running.")
        return

    # Stop the existing standalone Hecos before the daemon spawns a new one
    if is_hecos_running():
        print("[ORCHESTRATOR] Stopping standalone Hecos before starting Daemon...")
        stop_hecos()
        for _ in range(10):
            if not is_hecos_online():
                break
            time.sleep(0.5)
        if is_hecos_online():
            _kill_by_port()
            time.sleep(1)

    python_exe = get_platform_python()
    try:
        boot_log_path = os.path.join(_ROOT, "hecos", "logs", "hecos_boot_trace.log")
        boot_log = open(boot_log_path, "a", encoding="utf-8")
        boot_log.write(f"\n{'='*50}\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] ORCHESTRATOR: Spawning Hecos via Daemon Supervisor...\n{'='*50}\n")
        boot_log.flush()

        env = os.environ.copy()
        env["HECOS_MONITORED_PROCESS"] = "1"

        cmd = [python_exe, "-m", "hecos.core.daemon", "--web"]

        if sys.platform == "win32":
            _daemon_process = subprocess.Popen(
                cmd,
                cwd=_ROOT,
                stdout=boot_log,
                stderr=subprocess.STDOUT,
                creationflags=0x08000000,
                env=env
            )
        else:
            _daemon_process = subprocess.Popen(
                cmd,
                cwd=_ROOT,
                stdout=boot_log,
                stderr=subprocess.STDOUT,
                env=env
            )

        print("[ORCHESTRATOR] Hecos Supervisor (Daemon) spawned successfully.")
    except Exception as e:
        print(f"[ORCHESTRATOR] Failed to spawn Daemon: {e}")


def stop_daemon():
    """Terminates the Supervisor process (which will also kill its Hecos child)."""
    global _daemon_process
    if _daemon_process is not None:
        try:
            _daemon_process.terminate()
            _daemon_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _daemon_process.kill()
        except Exception:
            pass
        _daemon_process = None
        print("[ORCHESTRATOR] Daemon Supervisor stopped.")
    else:
        # If we lost the reference, fall back to killing by port
        _kill_by_port()


def is_daemon_running() -> bool:
    """Returns True if the Daemon Supervisor subprocess is alive."""
    global _daemon_process
    if _daemon_process is not None:
        if _daemon_process.poll() is None:
            return True
        _daemon_process = None
    return False


