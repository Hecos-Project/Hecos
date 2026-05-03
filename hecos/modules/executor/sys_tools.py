import os
import sys
import datetime
import subprocess

try:
    import winsound
    _HAS_WINSOUND = True
except ImportError:
    _HAS_WINSOUND = False

try:
    from hecos.core.logging import logger
except ImportError:
    class DummyLogger:
        def debug(self, *args, **kwargs): print("[EXE_DEBUG]", *args)
        def info(self, *args, **kwargs): print("[EXE_INFO]", *args)
        def error(self, *args, **kwargs): print("[EXE_ERR]", *args)
    logger = DummyLogger()

try:
    from app.config import ConfigManager
except ImportError:
    class DummyConfigMgr:
        def __init__(self): self.config = {}
        def get_plugin_config(self, tag, key, default): return default
    def FakeConfigManager(): return DummyConfigMgr()
    ConfigManager = FakeConfigManager

def get_time_tool() -> str:
    """Returns the current local time and date."""
    now = datetime.datetime.now()
    return f"Current local date and time: {now.strftime('%A, %d %B %Y — %H:%M')}"

def get_date_tool() -> str:
    """Returns the current local date."""
    return f"Today is: {datetime.date.today().strftime('%A, %d %B %Y')}"

def get_battery_status_tool() -> str:
    """Returns the battery level and charging status of the device."""
    try:
        import psutil
        b = psutil.sensors_battery()
        if b is None:
            return "No battery detected (desktop system or psutil unavailable)."
        charging = "Charging ⚡" if b.power_plugged else "On battery 🔋"
        return f"Battery: {b.percent:.0f}% — {charging}"
    except ImportError:
        return "Battery check requires psutil: pip install psutil"
    except Exception as e:
        return f"Battery check error: {e}"

def list_processes_tool() -> str:
    """Lists the top running processes on the system (name and PID)."""
    try:
        import psutil
        procs = sorted(psutil.process_iter(['pid', 'name', 'cpu_percent']),
                       key=lambda p: p.info['cpu_percent'] or 0, reverse=True)
        lines = ["Top Running Processes (by CPU):"]
        for p in procs[:20]:
            lines.append(f"  [{p.info['pid']}] {p.info['name']} — CPU: {p.info['cpu_percent']}%")
        return "\n".join(lines)
    except ImportError:
        # Fallback: use tasklist on Windows or ps on Linux
        try:
            if sys.platform == "win32":
                out = subprocess.check_output("tasklist", shell=True, text=True, errors='replace')
            else:
                out = subprocess.check_output("ps aux --sort=-%cpu | head -25", shell=True, text=True, errors='replace')
            return out[:2000]
        except Exception as e:
            return f"Process list error: {e}"
    except Exception as e:
        return f"Process list error: {e}"

def kill_process_tool(name: str) -> str:
    """
    Terminates a running process by name.
    :param name: The process name to terminate (e.g. 'notepad.exe').
    """
    try:
        import psutil
        killed = []
        for proc in psutil.process_iter(['name', 'pid']):
            if name.lower() in (proc.info['name'] or "").lower():
                proc.kill()
                killed.append(f"{proc.info['name']} (PID {proc.info['pid']})")
        if killed:
            return f"Terminated: {', '.join(killed)}"
        return f"No process named '{name}' found."
    except ImportError:
        try:
            if sys.platform == "win32":
                subprocess.run(f"taskkill /F /IM {name}", shell=True, check=False)
            else:
                subprocess.run(f"pkill -f {name}", shell=True, check=False)
            return f"Kill signal sent to '{name}'."
        except Exception as e:
            return f"Kill error: {e}"
    except Exception as e:
        return f"Kill error: {e}"

def reboot_system_tool() -> str:
    """Reboots the entire Hecos system (tray + web server)."""
    logger.info("System reboot triggered via EXECUTOR.")
    if _HAS_WINSOUND:
        winsound.Beep(600, 150)
        winsound.Beep(400, 150)
    os._exit(42)
    return "Rebooting..."

def execute_shell_command_tool(command: str, tag: str) -> str:
    """
    Executes a shell command (cmd.exe on Windows, bash on Linux).
    :param command: The shell command to run.
    """
    cfg = ConfigManager()
    if not cfg.get_plugin_config(tag, "enable_shell_commands", True):
        return "Error: Shell commands are disabled in configuration."
    try:
        output = subprocess.check_output(
            command, shell=True, text=True,
            errors='replace', stderr=subprocess.STDOUT, timeout=15
        )
        return output if output.strip() else "Command executed successfully (no output)."
    except subprocess.CalledProcessError as e:
        return f"Shell Error (exit code {e.returncode}): {e.output or str(e)}"
    except Exception as e:
        return f"Shell Error: {e}"
