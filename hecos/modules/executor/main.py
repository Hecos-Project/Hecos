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
    list_processes_tool, kill_process_tool, reboot_system_tool, execute_shell_command_tool,
    execute_background_command_tool, open_media_file_tool, get_date_tool, get_time_tool,
    get_battery_status_tool
)
from .sandbox import run_python_code_tool
from .file_manager import (
    read_file_tool, write_file_tool, patch_file_tool, 
    delete_file_tool, create_dir_tool, list_dir_tool
)
from .dev_tools import (
    project_tree_tool, search_code_tool, check_syntax_tool, run_project_test_tool
)

class ExecutorTools:
    """
    Hecos Executor — System Control, Code Jail, and File Management.
    Replaces and absorbs the former standalone AutoCoder plugin.
    """

    def __init__(self):
        self.tag = "EXECUTOR"
        self.desc = "Safe Python execution (AST Sandbox), developer tools, system control, and file management."
        self.status = "ONLINE (Core Tools Active)"

        self.config_schema = {
            "timeout_seconds": {
                "type": "int",
                "default": 10,
                "description": "Timeout in seconds for Python sandbox execution."
            },
            "test_timeout_seconds": {
                "type": "int",
                "default": 30,
                "description": "Timeout in seconds for run_project_test project execution."
            },
            "python_interpreter": {
                "type": "string",
                "default": "",
                "description": "Optional Python executable override for run_project_test (defaults to python_env\\python.exe)."
            },
            "enable_shell_commands": {
                "type": "bool",
                "default": True,
                "description": "Permits direct shell command execution (use with caution)."
            },
            "important_paths": {
                "type": "dict",
                "default": {},
                "description": "Dictionary of important paths for the AI to use."
            }
        }

        self.workspace_dir = self._resolve_workspace_dir()
        self.sandbox_dir = self._resolve_sandbox_dir()
        os.makedirs(self.workspace_dir, exist_ok=True)
        os.makedirs(self.sandbox_dir, exist_ok=True)

    _LEGACY_REL_PATHS = frozenset({
        "",
        ".",
        "./workspace",
        "workspace",
        "workspace/sandbox",
        "./workspace/sandbox",
    })

    def _resolve_media_managed_dir(self, configured_value: str, default_subpath: str) -> str:
        """Resolve a user-managed directory inside the hecos package tree (CWD-independent)."""
        hecos_pkg_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
        raw = (configured_value or "").strip()
        normalized = raw.replace("\\", "/").rstrip("/")
        if normalized in self._LEGACY_REL_PATHS:
            return os.path.normpath(os.path.join(hecos_pkg_dir, default_subpath))
        if os.path.isabs(raw):
            return os.path.abspath(raw)
        return os.path.normpath(os.path.join(hecos_pkg_dir, raw))

    def _resolve_workspace_dir(self) -> str:
        """Resolves persistent user projects dir from config (important_paths.projects), defaulting to hecos/media/workspace."""
        configured = ""
        try:
            import sys
            cfg_mgr = getattr(sys, "hecos_config_manager", None)
            if cfg_mgr:
                paths = cfg_mgr.get_plugin_config("EXECUTOR", "important_paths", {})
                if isinstance(paths, dict):
                    configured = paths.get("projects", "") or ""
        except Exception:
            pass
        return self._resolve_media_managed_dir(configured, os.path.join("media", "workspace"))

    def _resolve_sandbox_dir(self) -> str:
        """Resolves ephemeral AST sandbox execution dir from config (workspace_dir), defaulting to hecos/media/sandbox."""
        configured = ""
        try:
            import sys
            cfg_mgr = getattr(sys, "hecos_config_manager", None)
            if cfg_mgr:
                configured = cfg_mgr.get_plugin_config("EXECUTOR", "workspace_dir", "") or ""
        except Exception:
            pass
        return self._resolve_media_managed_dir(configured, os.path.join("media", "sandbox"))

    def _resolve_target_path(self, path: str) -> str:
        """Resolve relative paths inside the configured projects workspace."""
        clean = (path or "").strip()
        if not clean:
            return self._resolve_workspace_dir()
        if os.path.isabs(clean):
            return os.path.abspath(clean)
        return os.path.abspath(os.path.join(self._resolve_workspace_dir(), clean))

    # ── System Tools ──────────────────────────────────────────────────────────

    def execute_slash_command(self, command: str) -> str:
        """
        Executes an HDCS direct slash command (e.g. /img, /automation.click).
        Use this in Flows to run manual system commands bypassing the LLM.
        """
        try:
            from hecos.core.commands.executor import get_executor
            exc = get_executor()
            # Ensure command starts with slash
            cmd_str = command.strip()
            if not cmd_str.startswith("/"):
                cmd_str = "/" + cmd_str
            res = exc.execute(raw_input=cmd_str, page_context="flows", current_user_id="admin")
            if res.get("ok"):
                return res.get("output", "Success")
            else:
                return f"Error: {res.get('error', 'Unknown error')}\n{res.get('output', '')}"
        except Exception as e:
            return f"Exception executing command: {e}"

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

    def execute_background_command(self, command: str) -> str:
        return execute_background_command_tool(command, self.tag)

    def open_media_file(self, file_path: str) -> str:
        """
        Opens a media file (video, audio, image) using VLC if installed, otherwise the OS default player.
        Use this whenever the user asks to play, open, or reproduce a video or audio file.
        :param file_path: Absolute path to the media file (e.g. C:\\Users\\Tony\\Downloads\\movie.mkv).
        """
        return open_media_file_tool(file_path)

    # ── Code Sandbox ──────────────────────────────────────────────────────────

    def run_python_code(self, code: str) -> str:
        sandbox_dir = self._resolve_sandbox_dir()
        workspace_dir = self._resolve_workspace_dir()
        return run_python_code_tool(code, sandbox_dir, self.tag, projects_workspace_dir=workspace_dir)

    # ── File Management & Developer Tools ────────────────────────────────────

    def read_file(self, file_path: str, start_line: int = 1, end_line: int = -1) -> str:
        """
        Reads the contents of a file. Relative paths resolve inside the projects workspace.
        :param file_path: File path to read.
        :param start_line: First line to read (1-indexed). Default: 1.
        :param end_line: Last line to read (inclusive). Use -1 for the entire file.
        """
        return read_file_tool(self._resolve_target_path(file_path), start_line, end_line)

    def write_file(self, file_path: str, content: str, mode: str = "w") -> str:
        """
        Writes or creates a file and verifies it exists on disk. Relative paths resolve inside the projects workspace.
        :param file_path: File path to create or overwrite.
        :param content: Complete file text content to write.
        :param mode: 'w' to overwrite (default), 'a' to append.
        """
        return write_file_tool(self._resolve_target_path(file_path), content, mode)

    def patch_file(self, file_path: str, old_text: str, new_text: str) -> str:
        """
        Replaces the first exact occurrence of old_text with new_text in a file.
        :param file_path: File path to patch.
        :param old_text: Exact existing block to replace.
        :param new_text: Replacement text block.
        """
        return patch_file_tool(self._resolve_target_path(file_path), old_text, new_text)

    def delete_file(self, file_path: str) -> str:
        return delete_file_tool(self._resolve_target_path(file_path))

    def create_dir(self, directory_path: str) -> str:
        """
        Creates a directory and any missing parent folders.
        :param directory_path: Directory path to create.
        """
        return create_dir_tool(self._resolve_target_path(directory_path))

    def list_dir(self, directory_path: str) -> str:
        return list_dir_tool(self._resolve_target_path(directory_path))

    def project_tree(self, path: str = "", max_depth: int = 3) -> str:
        """
        Generates a compact project folder tree (skipping .git, __pycache__, python_env, node_modules).
        :param path: Root directory to inspect (defaults to projects workspace).
        :param max_depth: Maximum folder depth (1 to 6, default 3).
        """
        resolved = self._resolve_target_path(path) if path else self._resolve_workspace_dir()
        return project_tree_tool(resolved, max_depth=max_depth, default_workspace=self._resolve_workspace_dir())

    def search_code(self, query: str, path: str = "", file_glob: str = "") -> str:
        """
        Searches text/code recursively inside a project or module directory.
        :param query: Case-insensitive substring to find in files.
        :param path: Root directory or file to search (defaults to projects workspace).
        :param file_glob: Optional filename filter such as '*.py' or '*.js'.
        """
        resolved = self._resolve_target_path(path) if path else self._resolve_workspace_dir()
        return search_code_tool(query, path=resolved, file_glob=file_glob, default_workspace=self._resolve_workspace_dir())

    def check_syntax(self, file_path: str) -> str:
        """
        Checks syntax of a Python (.py), JSON (.json), YAML (.yaml/.yml), or JS (.js) file on disk.
        :param file_path: Path to the file to validate.
        """
        return check_syntax_tool(self._resolve_target_path(file_path))

    def run_project_test(self, target_path_or_command: str, cwd: str = "", timeout_seconds: int = 30) -> str:
        """
        Runs a real Python script, unittest, or pytest suite inside an authorized workspace/project using python_env.
        Unlike run_python_code, allows standard imports (os, sys, pathlib, requests, project modules).
        :param target_path_or_command: Script path (e.g. 'main.py') or test command (e.g. '-m unittest discover').
        :param cwd: Working directory for execution (defaults to projects workspace).
        :param timeout_seconds: Execution timeout in seconds (5 to 180, default 30).
        """
        work_dir = self._resolve_target_path(cwd) if cwd else self._resolve_workspace_dir()
        return run_project_test_tool(
            target_path_or_command=target_path_or_command,
            cwd=work_dir,
            timeout_seconds=timeout_seconds,
            default_workspace=self._resolve_workspace_dir(),
        )

    def set_important_path(self, name: str, path: str) -> str:
        """
        Memorizes an important directory path for the user (e.g. user_profile, downloads, projects).
        This path is permanently saved in Hecos configuration. Use this when the user asks you to remember a default path.
        """
        try:
            import sys
            cfg_mgr = getattr(sys, "hecos_config_manager", None)
            if not cfg_mgr:
                return "ConfigManager not available to save path permanently."
            
            paths = cfg_mgr.get_plugin_config("EXECUTOR", "important_paths", {})
            if not isinstance(paths, dict):
                paths = {}
            
            paths[name] = path
            cfg_mgr.set_plugin_config("EXECUTOR", "important_paths", paths)
            return f"Path '{name}' permanently set to '{path}'."
        except Exception as e:
            return f"Error setting path: {e}"

    def get_important_paths(self) -> str:
        """
        Returns all the important paths memorized by the user, plus the default sandbox workspace.
        Call this tool if you need to know where to save or look for user files.
        """
        try:
            import sys
            cfg_mgr = getattr(sys, "hecos_config_manager", None)
            paths = {}
            if cfg_mgr:
                paths = cfg_mgr.get_plugin_config("EXECUTOR", "important_paths", {})
            
            ws_dir = self._resolve_workspace_dir()
            sb_dir = self._resolve_sandbox_dir()
            if not paths:
                return f"No important paths memorized yet. Default workspace: {ws_dir} | Sandbox: {sb_dir}"
            
            res = "Memorized Important Paths:\n"
            for k, v in paths.items():
                res += f"- {k}: {v}\n"
            res += f"\nDefault Workspace: {ws_dir}\nSandbox Temp Dir: {sb_dir}\n"
            return res
        except Exception as e:
            return f"Error reading paths: {e}"


# ── Singleton ──────────────────────────────────────────────────────────────────
tools = ExecutorTools()

def info():
    return {
        "tag": tools.tag,
        "desc": tools.desc,
        "commands": {
            "run_python_code": "Execute Python safely in AST sandbox.",
            "execute_shell_command": "Run shell commands (cmd/bash).",
            "execute_background_command": "Run shell commands in background for long tasks.",
            "get_time": "Current local time and date.",
            "get_date": "Current local date.",
            "get_battery_status": "Device battery level and charging state.",
            "list_processes": "List top running processes.",
            "kill_process": "Terminate a process by name.",
            "reboot_system": "Restart the Hecos system.",
            "open_media_file": "Open a video or audio file with VLC or the OS default player. Use this to play any local media file.",
            "read_file": "Read a file's content by line range.",
            "write_file": "Write or create a file (overwrite or append).",
            "patch_file": "Surgically replace a text block inside a file.",
            "delete_file": "Delete a file.",
            "create_dir": "Create a directory tree.",
            "list_dir": "List a directory's contents.",
            "set_important_path": "Memorize an important directory path for the user (e.g., user_profile, downloads).",
            "get_important_paths": "Get all important paths memorized by the user, and the default workspace.",
            "project_tree": "Display a compact directory tree for a project or module.",
            "search_code": "Search code and configuration files for matching text.",
            "check_syntax": "Validate Python, JSON, YAML, or JavaScript file syntax.",
            "run_project_test": "Run a Python script, unittest, or pytest suite inside an authorized workspace/project.",
        }
    }

def status():
    return tools.status

def get_plugin():
    return tools


