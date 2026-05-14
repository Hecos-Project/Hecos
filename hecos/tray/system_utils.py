import sys
import subprocess
from hecos.tray.config import VERSION_FILE, _ROOT

# Global list of Popen objects for tracked console windows
_managed_consoles = []

def play_beep(freq: int, duration_ms: int):
    """Universal cross-platform audio helper for system beeps/cues."""
    if sys.platform == "win32":
        try:
            import winsound
            winsound.Beep(int(freq), int(duration_ms))
        except Exception:
            pass
    else:
        try:
            subprocess.run(["beep", "-f", str(freq), "-l", str(duration_ms)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            print('\a', end='', flush=True)

def get_version():
    try:
        with open(VERSION_FILE, "r") as f:
            return f.read().strip()
    except Exception:
        return "0.19.2"

def launch_console(script_path: str):
    """Launches a script in a new tracked console window."""
    global _managed_consoles
    _managed_consoles = [p for p in _managed_consoles if p.poll() is None]
    try:
        if sys.platform == "win32":
            p = subprocess.Popen(
                ["cmd.exe", "/c", script_path],
                creationflags=0x00000010,  # CREATE_NEW_CONSOLE
                cwd=_ROOT
            )
            _managed_consoles.append(p)
        else:
            p = subprocess.Popen(["x-terminal-emulator", "-e", script_path], cwd=_ROOT)
            _managed_consoles.append(p)
    except Exception as e:
        print(f"[TRAY] Failed to launch console: {e}")

def terminate_consoles():
    """Closes all console windows tracked by the Tray App."""
    global _managed_consoles
    for p in _managed_consoles:
        if p.poll() is None:
            try:
                p.terminate()
            except Exception:
                pass
    _managed_consoles = []
