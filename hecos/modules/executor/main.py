import os
import ast
import subprocess
import sys
import datetime
import shutil

try:
    import winsound
    _HAS_WINSOUND = True
except ImportError:
    _HAS_WINSOUND = False

try:
    from hecos.core.logging import logger
    from hecos.core.i18n import translator
    from app.config import ConfigManager
except ImportError:
    class DummyLogger:
        def debug(self, *args, **kwargs): print("[EXE_DEBUG]", *args)
        def info(self, *args, **kwargs): print("[EXE_INFO]", *args)
        def error(self, *args, **kwargs): print("[EXE_ERR]", *args)
    logger = DummyLogger()
    class DummyTranslator:
        def t(self, key, **kwargs): return key
    translator = DummyTranslator()
    class DummyConfigMgr:
        def __init__(self): self.config = {}
        def get_plugin_config(self, tag, key, default): return default
    ConfigManager = DummyConfigMgr

# ── Path Safety Guard ─────────────────────────────────────────────────────────
# Directories that Executor must never write to or delete from.
_FORBIDDEN_PREFIXES = (
    os.environ.get("SystemRoot", "C:\\Windows"),
    "C:\\Windows",
    "/etc", "/bin", "/sbin", "/usr/bin",
)

def _is_safe_path(path: str) -> bool:
    """Returns False if the resolved path points to a protected system directory."""
    abs_path = os.path.abspath(path)
    for forbidden in _FORBIDDEN_PREFIXES:
        if forbidden and abs_path.lower().startswith(os.path.abspath(forbidden).lower()):
            return False
    return True

# ── AST Security Analyzer (for run_python_code) ────────────────────────────────
FORBIDDEN_IMPORTS = {
    'os', 'sys', 'subprocess', 'shutil', 'socket', 'pathlib',
    'pty', 'tempfile', 'requests', 'urllib', 'ftplib', 'ctypes', 'winreg'
}
FORBIDDEN_CALLS = {'eval', 'exec', 'compile', 'open'}

class SecurityAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.errors = []

    def visit_Import(self, node):
        for alias in node.names:
            base_module = alias.name.split('.')[0]
            if base_module in FORBIDDEN_IMPORTS:
                self.errors.append(f"Forbidden import: {alias.name}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module:
            base_module = node.module.split('.')[0]
            if base_module in FORBIDDEN_IMPORTS:
                self.errors.append(f"Forbidden import from: {node.module}")
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            if node.func.id in FORBIDDEN_CALLS:
                self.errors.append(f"Forbidden function: {node.func.id}")
        self.generic_visit(node)


# ── Plugin Class ───────────────────────────────────────────────────────────────
class ExecutorTools:
    """
    Hecos Executor — System Control, Code Jail, and File Management.
    Replaces and absorbs the former standalone AutoCoder plugin.
    """

    def __init__(self):
        self.tag = "EXECUTOR"
        self.desc = "Safe Python execution (AST Sandbox), system control, and file management."
        self.status = "ONLINE (Core Tools Active)"

        self.config_schema = {
            "timeout_seconds": {
                "type": "int",
                "default": 10,
                "description": "Timeout in seconds for Python sandbox execution."
            },
            "enable_shell_commands": {
                "type": "bool",
                "default": True,
                "description": "Permits direct shell command execution (use with caution)."
            }
        }

        self.workspace_dir = os.path.abspath(os.path.join(os.getcwd(), "workspace", "sandbox"))
        os.makedirs(self.workspace_dir, exist_ok=True)

    # ── System Tools ──────────────────────────────────────────────────────────

    def get_time(self) -> str:
        """Returns the current local time and date."""
        now = datetime.datetime.now()
        return f"Current local date and time: {now.strftime('%A, %d %B %Y — %H:%M')}"

    def get_date(self) -> str:
        """Returns the current local date."""
        return f"Today is: {datetime.date.today().strftime('%A, %d %B %Y')}"

    def get_battery_status(self) -> str:
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

    def list_processes(self) -> str:
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

    def kill_process(self, name: str) -> str:
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

    def reboot_system(self) -> str:
        """Reboots the entire Hecos system (tray + web server)."""
        logger.info("System reboot triggered via EXECUTOR.")
        if _HAS_WINSOUND:
            winsound.Beep(600, 150)
            winsound.Beep(400, 150)
        os._exit(42)
        return "Rebooting..."

    def execute_shell_command(self, command: str) -> str:
        """
        Executes a shell command (cmd.exe on Windows, bash on Linux).
        :param command: The shell command to run.
        """
        cfg = ConfigManager()
        if not cfg.get_plugin_config(self.tag, "enable_shell_commands", True):
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

    # ── Code Sandbox ──────────────────────────────────────────────────────────

    def run_python_code(self, code: str) -> str:
        """
        Executes a block of Python code safely after strict Static Analysis (AST).
        Use for math, data manipulation, and algorithm building.
        :param code: The Python script to execute.
        """
        try:
            tree = ast.parse(code)
        except Exception as e:
            return f"Parsing Error: {e}"

        analyzer = SecurityAnalyzer()
        analyzer.visit(tree)
        if analyzer.errors:
            return f"SECURITY VIOLATION: {', '.join(analyzer.errors)}"

        script_path = os.path.join(self.workspace_dir, "ai_last_script.py")
        try:
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(code)
        except Exception as e:
            return f"I/O Error: {e}"

        cfg = ConfigManager()
        timeout = cfg.get_plugin_config(self.tag, "timeout_seconds", 10)
        try:
            process = subprocess.Popen(
                [sys.executable, script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                cwd=self.workspace_dir
            )
            output, _ = process.communicate(timeout=timeout)
            return output[-2000:] if len(output or "") > 2000 else (output or "")
        except subprocess.TimeoutExpired:
            process.kill()
            return f"Timeout Error: Execution expired after {timeout}s."
        except Exception as e:
            return f"Internal Error: {e}"

    # ── File Management (merged from AutoCoder) ───────────────────────────────

    def read_file(self, file_path: str, start_line: int = 1, end_line: int = -1) -> str:
        """
        Reads the contents of a file. Use start_line and end_line to limit output.
        :param file_path: Absolute path to the file to read.
        :param start_line: First line to read (1-indexed). Default: 1.
        :param end_line: Last line to read (inclusive). Use -1 for the entire file.
        """
        if not os.path.exists(file_path):
            return f"[EXECUTOR] File not found: {file_path}"
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            if end_line == -1:
                end_line = len(lines)
            chunk = "".join(lines[max(0, start_line - 1):end_line])
            return f"--- {file_path} (lines {start_line}–{end_line}) ---\n{chunk}"
        except Exception as e:
            return f"[EXECUTOR] Read error: {e}"

    def write_file(self, file_path: str, content: str, mode: str = "w") -> str:
        """
        Writes or creates a file. Mode 'w' overwrites; 'a' appends.
        :param file_path: Absolute path to the file to write or create.
        :param content: The full text content to write.
        :param mode: 'w' to overwrite (default), 'a' to append.
        """
        if not _is_safe_path(file_path):
            return "[EXECUTOR] ACCESS DENIED: Writing to system paths is forbidden."
        try:
            parent = os.path.dirname(os.path.abspath(file_path))
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(file_path, mode, encoding="utf-8") as f:
                f.write(content)
            logger.info(f"[EXECUTOR] write_file OK: {file_path} (mode={mode})")
            return f"[EXECUTOR] File written successfully: {file_path}"
        except Exception as e:
            return f"[EXECUTOR] Write error: {e}"

    def patch_file(self, file_path: str, old_text: str, new_text: str) -> str:
        """
        Replaces the first occurrence of old_text with new_text in a file.
        Use this for surgical edits instead of rewriting the entire file.
        Returns an error with a file preview if old_text is not found.
        :param file_path: Absolute path to the file to patch.
        :param old_text: The exact text block to find (whitespace must match exactly).
        :param new_text: The replacement text block.
        """
        if not _is_safe_path(file_path):
            return "[EXECUTOR] ACCESS DENIED: Patching system paths is forbidden."
        if not os.path.exists(file_path):
            return f"[EXECUTOR] File not found: {file_path}"
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                original = f.read()
            if old_text not in original:
                preview = original[:400].replace('\n', '↵')
                return f"[EXECUTOR] Text to replace not found. File starts with: {preview}..."
            patched = original.replace(old_text, new_text, 1)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(patched)
            logger.info(f"[EXECUTOR] patch_file OK: {file_path}")
            return f"[EXECUTOR] File patched successfully: {file_path}"
        except Exception as e:
            return f"[EXECUTOR] Patch error: {e}"

    def delete_file(self, file_path: str) -> str:
        """
        Deletes a file. Cannot delete directories.
        :param file_path: Absolute path to the file to delete.
        """
        if not _is_safe_path(file_path):
            return "[EXECUTOR] ACCESS DENIED: Deleting system paths is forbidden."
        if not os.path.exists(file_path):
            return f"[EXECUTOR] File not found: {file_path}"
        if os.path.isdir(file_path):
            return "[EXECUTOR] Path is a directory. Use execute_shell_command to remove directories."
        try:
            os.remove(file_path)
            logger.info(f"[EXECUTOR] delete_file OK: {file_path}")
            return f"[EXECUTOR] File deleted: {file_path}"
        except Exception as e:
            return f"[EXECUTOR] Delete error: {e}"

    def create_dir(self, directory_path: str) -> str:
        """
        Creates a directory (and all intermediate parents) if it does not exist.
        :param directory_path: Absolute path to the directory to create.
        """
        if not _is_safe_path(directory_path):
            return "[EXECUTOR] ACCESS DENIED: Creating system directories is forbidden."
        try:
            os.makedirs(directory_path, exist_ok=True)
            logger.info(f"[EXECUTOR] create_dir OK: {directory_path}")
            return f"[EXECUTOR] Directory created: {directory_path}"
        except Exception as e:
            return f"[EXECUTOR] Create dir error: {e}"

    def list_dir(self, directory_path: str) -> str:
        """
        Lists the files and subdirectories in a given directory.
        :param directory_path: Absolute path to the directory to list.
        """
        if not os.path.exists(directory_path):
            return f"[EXECUTOR] Directory not found: {directory_path}"
        try:
            items = os.listdir(directory_path)
            lines = [f"--- Contents of {directory_path} ({len(items)} items) ---"]
            for item in sorted(items):
                full = os.path.join(directory_path, item)
                tag = "[DIR] " if os.path.isdir(full) else "[FILE]"
                lines.append(f"  {tag} {item}")
            return "\n".join(lines)
        except Exception as e:
            return f"[EXECUTOR] List dir error: {e}"


# ── Singleton ──────────────────────────────────────────────────────────────────
tools = ExecutorTools()

def info():
    return {
        "tag": tools.tag,
        "desc": tools.desc,
        "commands": {
            "run_python_code": "Execute Python safely in AST sandbox.",
            "execute_shell_command": "Run shell commands (cmd/bash).",
            "get_time": "Current local time and date.",
            "get_date": "Current local date.",
            "get_battery_status": "Device battery level and charging state.",
            "list_processes": "List top running processes.",
            "kill_process": "Terminate a process by name.",
            "reboot_system": "Restart the Hecos system.",
            "read_file": "Read a file's content by line range.",
            "write_file": "Write or create a file (overwrite or append).",
            "patch_file": "Surgically replace a text block inside a file.",
            "delete_file": "Delete a file.",
            "create_dir": "Create a directory tree.",
            "list_dir": "List a directory's contents.",
        }
    }

def status():
    return tools.status

def get_plugin():
    return tools


