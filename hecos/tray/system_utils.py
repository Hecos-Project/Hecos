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
        with open(VERSION_FILE, "r", encoding="utf-8-sig") as f:
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

def get_hecos_processes():
    import os
    try:
        import psutil
    except ImportError:
        return []
        
    hecos_procs = []
    my_pid = os.getpid()
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            pid = proc.info['pid']
            if pid == my_pid:
                continue
                
            name = proc.info.get('name', '').lower()
            cmdline = proc.info.get('cmdline') or []
            cmd_str = " ".join(cmdline).lower()
            
            p_type = None
            
            if "pyrefly" in name or "antigravity" in cmd_str:
                continue

            if not ("python" in name or "piper" in name or "hecos" in name):
                continue
                
            if "piper" in name:
                p_type = "Piper TTS"
            elif "hecos.core.daemon" in cmd_str:
                p_type = "Hecos Daemon"
            elif "monitor.py" in cmd_str:
                p_type = "Monitor"
            elif "hecos.app.main" in cmd_str or "hecos_core" in name or "main.py" in cmd_str:
                p_type = "Hecos Core"
            elif "web_ui.server" in cmd_str or "hecos_web" in name:
                p_type = "Web Server"
            elif "tray" in cmd_str or "hecos_tray" in name:
                p_type = "Hecos Tray"
            elif "hecos_sdk.runner" in cmd_str or "hecos_module_" in name:
                p_type = "HPM Subprocess"
            elif "python" in name or "hecos" in name:
                if "hecos" in name or "hecos" in cmd_str:
                    p_type = "Hecos (Generic)"
                else:
                    continue

            if p_type:
                hecos_procs.append({
                    "pid": pid,
                    "type": p_type,
                    "cmd": " ".join(cmdline) or name
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return hecos_procs

def kill_all_hecos_processes():
    try:
        import psutil
    except ImportError:
        return 0
        
    procs = get_hecos_processes()
    killed = 0
    for p in procs:
        if p['type'] == "Hecos Tray":
            continue
        try:
            psutil.Process(p['pid']).kill()
            killed += 1
        except: pass
    return killed

def kill_duplicate_hecos_processes():
    try:
        import psutil
    except ImportError:
        return 0
        
    procs = get_hecos_processes()
    counts = {}
    for p in procs:
        counts[p['cmd']] = counts.get(p['cmd'], 0) + 1
        
    killed = 0
    for p in procs:
        if p['type'] == "Hecos Tray":
            continue
        if counts[p['cmd']] > 1:
            try:
                psutil.Process(p['pid']).kill()
                counts[p['cmd']] -= 1
                killed += 1
            except: pass
    return killed
