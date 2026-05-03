import os

try:
    from hecos.core.i18n import translator
    from app.config import ConfigManager
except ImportError:
    class DummyTranslator:
        def t(self, key, **kwargs): return key
    translator = DummyTranslator()
    
    class DummyConfigMgr:
        def __init__(self): self.config = {}
        def get_plugin_config(self, tag, key, default): return default
    def FakeConfigManager(): return DummyConfigMgr()
    ConfigManager = FakeConfigManager

# Relative imports from our extracted modules
from .sys_tools import (
    get_time_tool, get_date_tool, get_battery_status_tool, 
    list_processes_tool, kill_process_tool, reboot_system_tool, execute_shell_command_tool
)
from .sandbox import run_python_code_tool
from .file_manager import (
    read_file_tool, write_file_tool, patch_file_tool, 
    delete_file_tool, create_dir_tool, list_dir_tool
)

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
        return get_time_tool()

    def get_date(self) -> str:
        return get_date_tool()

    def get_battery_status(self) -> str:
        return get_battery_status_tool()

    def list_processes(self) -> str:
        return list_processes_tool()

    def kill_process(self, name: str) -> str:
        return kill_process_tool(name)

    def reboot_system(self) -> str:
        return reboot_system_tool()

    def execute_shell_command(self, command: str) -> str:
        return execute_shell_command_tool(command, self.tag)

    # ── Code Sandbox ──────────────────────────────────────────────────────────

    def run_python_code(self, code: str) -> str:
        return run_python_code_tool(code, self.workspace_dir, self.tag)

    # ── File Management ───────────────────────────────────────────────────────

    def read_file(self, file_path: str, start_line: int = 1, end_line: int = -1) -> str:
        return read_file_tool(file_path, start_line, end_line)

    def write_file(self, file_path: str, content: str, mode: str = "w") -> str:
        return write_file_tool(file_path, content, mode)

    def patch_file(self, file_path: str, old_text: str, new_text: str) -> str:
        return patch_file_tool(file_path, old_text, new_text)

    def delete_file(self, file_path: str) -> str:
        return delete_file_tool(file_path)

    def create_dir(self, directory_path: str) -> str:
        return create_dir_tool(directory_path)

    def list_dir(self, directory_path: str) -> str:
        return list_dir_tool(directory_path)


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


