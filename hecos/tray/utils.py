import sys
import os
import subprocess
from hecos.tray.config import SYSTEM_YAML, HECOS_PORT, VERSION_FILE, _ROOT

# Global list of Popen objects for tracked console windows
_managed_consoles = []

def get_scheme() -> str:
    """Reads system.yaml to detect if HTTPS is enabled."""
    try:
        with open(SYSTEM_YAML, "r", encoding="utf-8") as f:
            content = f.read()
        in_webui = False
        for line in content.splitlines():
            stripped = line.strip()
            if "WEB_UI:" in stripped:
                in_webui = True
            if in_webui and "https_enabled:" in stripped:
                value = stripped.split(":", 1)[1].strip().lower()
                if value in ("true", "yes", "1"):
                    return "https"
                break
    except Exception:
        pass
    return "http"

def play_beep(freq: int, duration_ms: int):
    """Universal cross-platform audio helper for system beeps/cues."""
    import sys
    if sys.platform == "win32":
        try:
            import winsound
            winsound.Beep(int(freq), int(duration_ms))
        except: pass
    else:
        try:
            import subprocess
            subprocess.run(["beep", "-f", str(freq), "-l", str(duration_ms)], 
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except:
            print('\a', end='', flush=True)

def get_urls():
    scheme = get_scheme()
    base = f"{scheme}://localhost:{HECOS_PORT}"
    return f"{base}/chat", f"{base}/hecos/config/ui"

def get_version():
    try:
        with open(VERSION_FILE, "r") as f:
            return f.read().strip()
    except Exception:
        return "0.19.1"

def is_hecos_online():
    """Checks if the Hecos backend is responding on port 7070."""
    import socket
    try:
        with socket.create_connection(("localhost", HECOS_PORT), timeout=2):
            return True
    except OSError:
        return False

def get_lan_ip() -> str:
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.254.254.254", 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "N/A"

def launch_console(script_path: str):
    """Launches a script in a new tracked console window."""
    global _managed_consoles
    # Clean up dead handles first
    _managed_consoles = [p for p in _managed_consoles if p.poll() is None]
    
    try:
        if sys.platform == "win32":
            # CREATE_NEW_CONSOLE = 0x00000010
            p = subprocess.Popen(
                ["cmd.exe", "/c", script_path],
                creationflags=0x00000010,
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
            except: pass
    _managed_consoles = []
