import os
import sys
import datetime
import subprocess
import re
import shlex
import uuid

try:
    import winsound
    _HAS_WINSOUND = True
except ImportError:
    _HAS_WINSOUND = False

try:
    from hecos.core.logging import logger
    from hecos.core.agent.traces import AgentTracer
except ImportError:
    class DummyLogger:
        def debug(self, *args, **kwargs): print("[EXE_DEBUG]", *args)
        def info(self, *args, **kwargs): print("[EXE_INFO]", *args)
        def error(self, *args, **kwargs): print("[EXE_ERR]", *args)
    logger = DummyLogger()
    class DummyTracer:
        @staticmethod
        def emit_action(t, c, o): print(f"[ACTION] {t}: {c}\n{o}")
    AgentTracer = DummyTracer()

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

# Matches: pip install ..., pip3 install ..., python -m pip install ..., py -3 -m pip install ...
_PIP_INSTALL_RE = re.compile(
    r'^\s*(?:(?:"[^"]*python[^"]*"|[^\s"]*python[\w.]*(?:\.exe)?|py(?:\.exe)?)(?:\s+-\d(?:\.\d+)?)?\s+-m\s+)?'
    r'pip[\d.]*(?:\.exe)?\s+install\b(?P<rest>.*)$',
    re.IGNORECASE | re.DOTALL,
)
_SHELL_META_RE = re.compile(r'&&|\|\||[|;<>&`\n]')
_PIP_RAW_LINE_RE = re.compile(r'^\s*Progress\s+\d+\s+of\s+\d+\s*$', re.IGNORECASE)
_PIP_VALUE_FLAGS = {
    "-t", "--target", "-r", "--requirement", "-c", "--constraint", "-i", "--index-url",
    "--extra-index-url", "-f", "--find-links", "--prefix", "--root", "--progress-bar",
}


def _run_pip_with_progress(command: str, tag: str):
    """
    If `command` is a plain `pip install ...`, runs it through the unified progress
    system (bars in logs, CLI, Presenter, WebUI) and returns the textual result.
    Returns None when the command is not eligible, so the caller falls back to the shell.
    """
    m = _PIP_INSTALL_RE.match(command)
    if not m:
        return None
    rest = m.group("rest")
    # Compound commands (pipes, chaining, redirects) must be handled by the real shell.
    if _SHELL_META_RE.search(re.sub(r'"[^"]*"|\'[^\']*\'', '', rest)):
        return None
    try:
        args = shlex.split(rest, posix=(os.name != "nt"))
    except ValueError:
        return None
    args = [a[1:-1] if len(a) >= 2 and a[0] == a[-1] and a[0] in "\"'" else a for a in args]
    if not args or any(a in ("-h", "--help") for a in args):
        return None

    try:
        from hecos.core.progress import progress
        from hecos.core.progress.adapters.pip import PIP_PHASES
    except Exception:
        return None

    pkgs, skip_next = [], False
    for a in args:
        if skip_next:
            skip_next = False
            continue
        if a in _PIP_VALUE_FLAGS:
            skip_next = True
            continue
        if not a.startswith("-"):
            pkgs.append(os.path.basename(a) if os.path.sep in a else a)
    title = "pip install " + " ".join(pkgs)[:60]
    retcode, output = -1, "Operation cancelled."
    with progress.task(
        f"exec_pip_{uuid.uuid4().hex[:8]}",
        title=title,
        source=tag,
        phases=list(PIP_PHASES),
    ) as pt:
        retcode, output = progress.pip(["install"] + args, task=pt)
        if retcode != 0:
            tail = [l for l in output.strip().splitlines() if l.strip()][-1:] or ["pip failed"]
            pt.fail(f"pip exited with code {retcode}: {tail[0][:200]}")

    clean_output = "".join(
        l for l in output.splitlines(keepends=True) if not _PIP_RAW_LINE_RE.match(l)
    )
    if retcode != 0:
        return f"Shell Error (exit code {retcode}): {clean_output or 'pip install failed.'}"
    return clean_output if clean_output.strip() else "Command executed successfully (no output)."


def execute_shell_command_tool(command: str, tag: str) -> str:
    """
    Executes a shell command (cmd.exe on Windows, bash on Linux).
    :param command: The shell command to run.
    """
    cfg = ConfigManager()
    if not cfg.get_plugin_config(tag, "enable_shell_commands", True):
        return "Error: Shell commands are disabled in configuration."
    pip_result = None
    try:
        pip_result = _run_pip_with_progress(command, tag)
    except Exception as e:
        # pip may already have run: never re-run it through the plain shell.
        logger.error(f"[EXECUTOR] pip progress wrapper failed: {e}")
        pip_result = f"Shell Error: pip install did not complete cleanly: {e}"
    if pip_result is not None:
        AgentTracer.emit_action(tag, command, pip_result)
        return pip_result
    try:
        output = subprocess.check_output(
            command, shell=True, text=True,
            errors='replace', stderr=subprocess.STDOUT, timeout=300
        )
        final_output = output if output.strip() else "Command executed successfully (no output)."
        AgentTracer.emit_action(tag, command, final_output)
        return final_output
    except subprocess.CalledProcessError as e:
        err_msg = f"Shell Error (exit code {e.returncode}): {e.output or str(e)}"
        AgentTracer.emit_action(tag, command, err_msg)
        return err_msg
    except Exception as e:
        err_msg = f"Shell Error: {e}"
        AgentTracer.emit_action(tag, command, err_msg)
        return err_msg

def execute_background_command_tool(command: str, tag: str) -> str:
    """
    Executes a shell command in the background, writing output to a log file.
    Use for long-running installations or tasks.
    """
    cfg = ConfigManager()
    if not cfg.get_plugin_config(tag, "enable_shell_commands", True):
        return "Error: Shell commands are disabled in configuration."
    try:
        import uuid
        log_dir = os.path.abspath(os.path.join(os.getcwd(), "hecos", "logs", "background_tasks"))
        os.makedirs(log_dir, exist_ok=True)
        task_id = str(uuid.uuid4())[:8]
        log_file = os.path.join(log_dir, f"cmd_log_{task_id}.txt")
        
        # Open log file
        f = open(log_file, "w", encoding="utf-8")
        f.write(f"--- Background Task Started ---\nCommand: {command}\n\n")
        f.flush()
        
        # Start background process
        # On Windows, we use CREATE_NO_WINDOW if possible, or just regular Popen
        kwargs = {}
        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        
        proc = subprocess.Popen(
            command, shell=True, stdout=f, stderr=subprocess.STDOUT, text=True, **kwargs
        )
        
        msg = f"Background command started successfully.\nPID: {proc.pid}\nLog file: {log_file}\n\nYou can use the read_file tool later to check the progress or outcome."
        AgentTracer.emit_action(tag, command, msg)
        return msg
    except Exception as e:
        err_msg = f"Failed to start background command: {e}"
        AgentTracer.emit_action(tag, command, err_msg)
        return err_msg

def open_media_file_tool(file_path: str) -> str:
    """
    Opens a media file (video, audio, image) with the best available player.
    Tries VLC first (64-bit, then 32-bit), then falls back to the OS default.
    Launches the player as a fully detached process so the UI is not blocked.
    :param file_path: Absolute path to the media file to open.
    """
    import shlex

    path = file_path.strip().strip('"').strip("'")

    if not os.path.exists(path):
        return f"❌ File not found: {path}"

    vlc_candidates = [
        r"C:\Program Files\VideoLAN\VLC\vlc.exe",
        r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\VideoLAN\VLC\vlc.exe"),
    ]
    vlc_exe = next((c for c in vlc_candidates if os.path.isfile(c)), None)

    try:
        if vlc_exe:
            # Launch VLC fully detached — no console, no wait
            kwargs = {}
            if sys.platform == "win32":
                kwargs["creationflags"] = (
                    subprocess.DETACHED_PROCESS |
                    subprocess.CREATE_NEW_PROCESS_GROUP |
                    subprocess.CREATE_NO_WINDOW
                )
            subprocess.Popen([vlc_exe, path], **kwargs)
            fname = os.path.basename(path)
            AgentTracer.emit_action("EXECUTOR", f"open_media_file: {path}", f"Launched VLC → {fname}")
            return f"✅ VLC avviato con: `{fname}`"
        else:
            # Fallback: OS default player via os.startfile (Windows) or xdg-open (Linux)
            if sys.platform == "win32":
                os.startfile(path)
            else:
                subprocess.Popen(["xdg-open", path])
            fname = os.path.basename(path)
            AgentTracer.emit_action("EXECUTOR", f"open_media_file: {path}", f"Opened with OS default → {fname}")
            return f"✅ Aperto con il player predefinito del sistema: `{fname}` (VLC non trovato nei percorsi standard)"
    except Exception as e:
        err = f"❌ Impossibile aprire il file: {e}"
        AgentTracer.emit_action("EXECUTOR", f"open_media_file: {path}", err)
        return err
