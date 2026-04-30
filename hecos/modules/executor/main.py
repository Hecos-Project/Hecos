import os
import ast
import subprocess
import sys
import datetime
import winsound
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

# --- AST SECURITY ANALYZER ---
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
                self.errors.append(f"Import non consentito: {alias.name}")
        self.generic_visit(node)
        
    def visit_ImportFrom(self, node):
        if node.module:
            base_module = node.module.split('.')[0]
            if base_module in FORBIDDEN_IMPORTS:
                self.errors.append(f"Import non consentito da: {node.module}")
        self.generic_visit(node)
        
    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            if node.func.id in FORBIDDEN_CALLS:
                self.errors.append(f"Funzione non consentita: {node.func.id}")
        self.generic_visit(node)

# --- PLUGIN CLASS ---
class ExecutorTools:
    """
    Plugin: Hecos Code Jail (AST Sandbox)
    Allows safe algorithmic execution and root system control.
    """

    def __init__(self):
        self.tag = "EXECUTOR"
        self.desc = "Safe Python execution (AST Sandbox) and System Control."
        self.status = "ONLINE (Core Tools Active)"
        
        self.config_schema = {
            "timeout_seconds": {
                "type": "int",
                "default": 10,
                "description": "Timeout in secondi per prevenire loop infiniti."
            },
            "enable_shell_commands": {
                "type": "bool",
                "default": True,
                "description": "Permette l'esecuzione di comandi shell diretti (pericoloso)."
            }
        }
        
        self.workspace_dir = os.path.abspath(os.path.join(os.getcwd(), "workspace", "sandbox"))
        os.makedirs(self.workspace_dir, exist_ok=True)

    # --- NATIVE TOOLS (Bypass Sandbox) ---

    def get_time(self) -> str:
        """Returns the current local time."""
        ora = datetime.datetime.now().strftime("%H:%M")
        return f"Current local time: {ora}"

    def reboot_system(self) -> str:
        """Reboots the entire Hecos system."""
        logger.info("System reboot triggered via EXECUTOR.")
        if sys.platform == "win32":
            winsound.Beep(600, 150)
            winsound.Beep(400, 150)
        os._exit(42)
        return "Rebooting..."

    def execute_shell_command(self, command: str) -> str:
        """Executes a shell command (cmd.exe) in the background."""
        cfg = ConfigManager()
        if not cfg.get_plugin_config(self.tag, "enable_shell_commands", True):
            return "Error: Shell commands are disabled in configuration."

        try:
            output = subprocess.check_output(command, shell=True, text=True, errors='replace', stderr=subprocess.STDOUT, timeout=15)
            return output if output.strip() else "Command executed successfully (no output)."
        except Exception as e:
            return f"Shell Error: {e}"

    # --- SANDBOXED TOOLS ---

    def run_python_code(self, code: str) -> str:
        """
        Executes a block of Python code safely after strict Static Analysis.
        Use for math, data manipulation, algorithm building.
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

# Singleton
tools = ExecutorTools()

# --- Plugin standard interface ---
def info():
    return {
        "tag": tools.tag,
        "desc": tools.desc,
        "commands": {
            "run_python_code": "Esegui script Python in sandbox sicura.",
            "execute_shell_command": "Esegui comandi CMD nel sistema.",
            "get_time": "Ottieni l'ora locale corrente.",
            "reboot_system": "Riavvia il sistema Hecos."
        }
    }

def status():
    return tools.status

def get_plugin():
    return tools
