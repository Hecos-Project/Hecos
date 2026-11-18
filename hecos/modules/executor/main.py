import os
import re

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
    AgentTracer, logger, sanitize_llm_path, read_file_tool, write_file_tool, patch_file_tool,
    delete_file_tool, create_dir_tool, list_dir_tool, move_path_tool
)
from .dev_tools import (
    project_tree_tool, search_code_tool, check_syntax_tool,
    run_project_test_tool, inspect_web_project_issues
)
from .code_intel import build_repo_map
from .git_tools import (
    git_status_tool, git_diff_tool, git_checkpoint_tool, git_restore_tool
)
from .aider_bridge import run_aider_task_tool
from .process_runner import (
    get_process_registry,
    probe_local_http_url,
    resolve_authorized_target,
    run_tests_for_target,
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
            "coding_enabled": {
                "type": "bool",
                "default": False,
                "description": "Enable the Coding Environment & Workspace Runner button in the Chat topbar (disabled by default)."
            },
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
            },
            "auto_verify_syntax_on_write": {
                "type": "bool",
                "default": True,
                "description": "Automatically verify syntax after writing or patching code/config files."
            },
            "auto_run_existing_tests_on_write": {
                "type": "bool",
                "default": True,
                "description": "Automatically run matching existing workspace unit tests after editing Python files."
            },
            "auto_generate_unit_tests": {
                "type": "bool",
                "default": False,
                "description": "Encourage coding presets to generate companion unit tests automatically for new modules."
            },
            "default_run_timeout_seconds": {
                "type": "int",
                "default": 30,
                "description": "Default timeout in seconds when running scripts or test suites."
            },
            "allow_ui_script_execution": {
                "type": "bool",
                "default": True,
                "description": "Allow launching workspace scripts and tests directly from chat cards and Workspace Runner UI."
            },
            "aider_enabled": {
                "type": "bool",
                "default": True,
                "description": "Enable invisible Aider sidecar delegation for multi-file coding tasks."
            },
            "aider_global_preset": {
                "type": "string",
                "default": "hecos_coder",
                "description": "Default Global Preset ID used by Aider (provides model, backend, and num_ctx unless overridden)."
            },
            "aider_model": {
                "type": "string",
                "default": "",
                "description": "Optional LiteLLM/Ollama model override for Aider (empty = use Global Preset / active model)."
            },
            "aider_num_ctx": {
                "type": "int",
                "default": 0,
                "description": "Optional context window override for Ollama (0 = inherit from Global Preset or 16384 fallback)."
            },
            "aider_edit_format": {
                "type": "string",
                "default": "",
                "description": "Optional Aider edit format override (e.g. diff, whole, udiff)."
            },
            "aider_auto_lint": {
                "type": "bool",
                "default": True,
                "description": "Let Aider run automatic syntax/lint checks after editing files."
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
        clean = sanitize_llm_path(path)
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

    def execute_shell_command(self, command: str, cwd: str = "") -> str:
        """
        Executes a shell command with python_env tools (pytest, ruff, uv, python) on PATH.
        :param command: Shell command to execute.
        :param cwd: Optional working directory (workspace-relative or absolute path).
        """
        resolved_cwd = self._resolve_target_path(cwd) if cwd and str(cwd).strip() else ""
        return execute_shell_command_tool(command, self.tag, cwd=resolved_cwd)

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

    _AUTO_CHECK_EXTS = frozenset({
        ".py", ".json", ".yaml", ".yml",
        ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".css", ".html", ".htm",
    })
    _WEB_DIAG_EXTS = frozenset({".py", ".html", ".htm"})

    def _get_exec_config(self, key: str, default):
        try:
            import sys
            cfg_mgr = getattr(sys, "hecos_config_manager", None)
            if cfg_mgr:
                return cfg_mgr.get_plugin_config(self.tag, key, default)
        except Exception:
            pass
        return default

    def _run_post_write_verification(self, abs_path: str) -> str:
        """Run deterministic post-write syntax verification, web/Flask diagnostics, and matching project tests."""
        ext = os.path.splitext(abs_path)[1].lower()
        if (ext not in self._AUTO_CHECK_EXTS and ext not in self._WEB_DIAG_EXTS) or not os.path.isfile(abs_path):
            return ""

        notes = []
        syntax_ok = True
        if ext in self._AUTO_CHECK_EXTS and bool(self._get_exec_config("auto_verify_syntax_on_write", True)):
            syntax_res = check_syntax_tool(abs_path)
            syntax_ok = "SYNTAX ERROR" not in syntax_res
            notes.append(f"[AUTO-CHECK] {syntax_res}")
            if not syntax_ok:
                m_ln = re.search(r"line\s+(\d+)", syntax_res)
                if m_ln:
                    err_ln = max(1, int(m_ln.group(1)))
                    excerpt = read_file_tool(
                        abs_path,
                        start_line=max(1, err_ln - 8),
                        end_line=err_ln + 8,
                    )
                    notes.append(
                        f"[ERROR CONTEXT around line {err_ln}]:\n{excerpt}\n"
                        "[ACTION REQUIRED]: Fix the syntax error shown in the numbered lines above before running tests or starting the app."
                    )

        if ext in self._WEB_DIAG_EXTS:
            for warn in inspect_web_project_issues(abs_path):
                notes.append(f"[WEB-DIAGNOSTIC] {warn}")

        ws_dir = self._resolve_workspace_dir()
        in_workspace = os.path.abspath(abs_path).lower().startswith(os.path.abspath(ws_dir).lower())
        if syntax_ok and ext == ".py" and in_workspace and bool(self._get_exec_config("auto_run_existing_tests_on_write", True)):
            timeout = self._get_exec_config("default_run_timeout_seconds", 30)
            test_res = run_tests_for_target(
                abs_path,
                ws_dir,
                timeout_seconds=timeout,
                strict_workspace_only=True,
            )
            if not test_res.get("no_tests_found"):
                status_label = "PASSED" if test_res.get("ok") else "FAILED"
                out_tail = (test_res.get("output") or "").strip()[-1200:]
                logger.info(
                    f"[EXECUTOR] post-write test {status_label}: {os.path.basename(abs_path)} exit={test_res.get('exit_code')}"
                )
                notes.append(
                    f"[AUTO-TEST] {status_label} (exit={test_res.get('exit_code')}, {test_res.get('duration_ms', 0)}ms):\n{out_tail}"
                )

        return ("\n" + "\n".join(notes)) if notes else ""

    def write_file(self, file_path: str, content: str, mode: str = "w") -> str:
        """
        Writes or creates a file and verifies it exists on disk. Relative paths resolve inside the projects workspace.
        :param file_path: File path to create or overwrite.
        :param content: Complete file text content to write.
        :param mode: 'w' to overwrite (default), 'a' to append.
        """
        resolved = self._resolve_target_path(file_path)
        res = write_file_tool(resolved, content, mode)
        if res.startswith("[EXECUTOR] File verified on disk:"):
            res += self._run_post_write_verification(resolved)
        return res

    def patch_file(
        self,
        file_path: str,
        old_text: str,
        new_text: str,
        start_line: int = 0,
        end_line: int = 0,
    ) -> str:
        """
        Replaces a unique existing occurrence of old_text with new_text in a file.
        :param file_path: File path to patch.
        :param old_text: Exact existing block to replace.
        :param new_text: Replacement text block.
        :param start_line: Optional 1-indexed start line to scope the replacement.
        :param end_line: Optional 1-indexed end line to scope the replacement.
        """
        resolved = self._resolve_target_path(file_path)
        res = patch_file_tool(resolved, old_text, new_text, start_line=start_line, end_line=end_line)
        if res.startswith("[EXECUTOR] File patched and verified on disk:"):
            res += self._run_post_write_verification(resolved)
        return res

    def move_path(self, src_path: str, dst_path: str) -> str:
        """
        Moves or renames a file or folder inside the authorized workspace.
        :param src_path: Source file or directory path.
        :param dst_path: Destination file or directory path.
        """
        return move_path_tool(self._resolve_target_path(src_path), self._resolve_target_path(dst_path))

    def repo_map(self, path: str = "", max_files: int = 60, max_lines: int = 160) -> str:
        """
        Generates a compact multi-language AST map (files, classes, functions, line numbers) for a codebase.
        :param path: Project root directory (defaults to projects workspace).
        :param max_files: Maximum files to inspect (default 60).
        :param max_lines: Maximum output lines (default 160).
        """
        resolved = self._resolve_target_path(path) if path else self._resolve_workspace_dir()
        return build_repo_map(resolved, max_files=max_files, max_lines=max_lines)

    def git_status(self, repo_path: str = "") -> str:
        """
        Inspects Git branch and modified/untracked files inside a project repository.
        :param repo_path: Repository path (defaults to projects workspace).
        """
        resolved = self._resolve_target_path(repo_path) if repo_path else self._resolve_workspace_dir()
        return git_status_tool(resolved)

    def git_diff(self, repo_path: str = "", file_path: str = "", staged: bool = False) -> str:
        """
        Shows unified Git diff (size-capped) for the repository or a specific file.
        :param repo_path: Repository path (defaults to projects workspace).
        :param file_path: Optional file path filter inside the repository.
        :param staged: When true, inspect staged changes instead of unstaged changes.
        """
        resolved = self._resolve_target_path(repo_path) if repo_path else self._resolve_workspace_dir()
        return git_diff_tool(resolved, file_path=file_path, staged=staged)

    def git_checkpoint(self, repo_path: str = "", message: str = "hecos checkpoint") -> str:
        """
        Saves a non-destructive Git checkpoint snapshot (tracked + untracked files) without mutating HEAD.
        :param repo_path: Project or repository directory (auto-initializes .git if missing).
        :param message: Short label describing the checkpoint.
        """
        resolved = self._resolve_target_path(repo_path) if repo_path else self._resolve_workspace_dir()
        return git_checkpoint_tool(resolved, message=message, auto_init=True)

    def git_restore(
        self,
        repo_path: str = "",
        file_path: str = "",
        target_ref: str = "HEAD",
        confirm_all: bool = False,
    ) -> str:
        """
        Restores a file (or the full tree when confirm_all=True) from HEAD or a saved checkpoint ('latest' or SHA).
        :param repo_path: Project or repository directory.
        :param file_path: File path inside the repo to restore.
        :param target_ref: Git ref, commit SHA, or 'latest' for the last checkpoint.
        :param confirm_all: Must be true if restoring all tracked files without specifying file_path.
        """
        resolved = self._resolve_target_path(repo_path) if repo_path else self._resolve_workspace_dir()
        return git_restore_tool(resolved, file_path=file_path, target_ref=target_ref, confirm_all=confirm_all)

    def run_aider_task(self, repo_path: str, instruction: str, files: str = "", model: str = "") -> str:
        """
        Delegates a multi-file refactor/generation task to isolated Aider CLI (if installed).
        :param repo_path: Target Git project directory.
        :param instruction: Detailed coding task prompt for Aider.
        :param files: Optional comma-separated list of target file paths.
        :param model: Optional LiteLLM/Ollama model override (e.g. 'ollama_chat/qwen2.5-coder:14b').
        """
        resolved = self._resolve_target_path(repo_path) if repo_path else self._resolve_workspace_dir()
        return run_aider_task_tool(resolved, instruction=instruction, files=files, model=model)

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

    def start_app(self, target_path: str, args: str = "", wait_seconds: float = 2.5) -> str:
        """
        Starts a persistent workspace script, local web server (Flask/FastAPI/Streamlit), or desktop GUI app
        using ManagedProcessRegistry with logs saved under media/sandbox/runs.
        :param target_path: Workspace-relative or authorized path to the script to launch.
        :param args: Optional CLI arguments string.
        :param wait_seconds: Initial startup wait window in seconds to capture banner/URL or immediate errors.
        """
        ws_dir = self._resolve_workspace_dir()
        sb_dir = self._resolve_sandbox_dir()
        res = get_process_registry().start_target(
            target_path,
            ws_dir,
            sb_dir,
            args=args,
            wait_seconds=wait_seconds,
            strict_workspace_only=False,
            require_stay_alive=False,
        )
        if not res.get("ok") and res.get("status") == "error":
            logger.warning(f"[EXECUTOR] start_app failed for {target_path}: {res.get('error')}")
            return f"[EXECUTOR] {res.get('error', 'Failed to start application.')}"
        lines = [
            f"[EXECUTOR] Process {res.get('status', 'unknown').upper()} | run_id={res.get('run_id')} | PID={res.get('pid')} | file={res.get('path')}",
        ]
        if res.get("log_path"):
            lines.append(f"Log File: {res.get('log_path')}")
        if res.get("exit_code") is not None:
            lines.append(f"Exit Code: {res.get('exit_code')}")
        urls = res.get("detected_urls") or []
        if urls:
            lines.append("Detected URL(s): " + ", ".join(urls))
        probe = res.get("http_probe")
        if isinstance(probe, dict):
            if probe.get("ok"):
                lines.append(f"[HEALTH-CHECK OK] {probe.get('url')} -> {probe.get('summary')}")
            else:
                lines.append(
                    f"[HEALTH-CHECK FAILED] {probe.get('url')} -> {probe.get('summary')} "
                    "(fix templates/static/routes before finishing!)"
                )
                target_file = res.get("path")
                if target_file:
                    for diag in inspect_web_project_issues(target_file):
                        lines.append(f"[WEB-DIAGNOSTIC] {diag}")
        out = (res.get("output") or "").strip()[-1800:]
        if out:
            lines.append(f"--- LOG ---\n{out}")
        return "\n".join(lines)

    def probe_url(self, url: str) -> str:
        """
        Tests a local running web server URL (http://127.0.0.1:<port> or http://localhost:<port>),
        verifies the HTML HTTP status, and checks referenced local CSS/JS assets for 404/500 errors.
        :param url: Local URL to probe (e.g. 'http://127.0.0.1:5000/').
        """
        res = probe_local_http_url(url, timeout=2.5, check_assets=True, retries=2)
        AgentTracer.emit_action("probe_url", url, res.get("summary") or res.get("error", ""))
        if res.get("ok"):
            return f"[EXECUTOR] [HEALTH-CHECK OK] {res.get('url')} -> {res.get('summary')}"
        return f"[EXECUTOR] [HEALTH-CHECK FAILED] {res.get('url')} -> {res.get('summary') or res.get('error')}"

    def get_app_logs(self, run_id: str, tail_lines: int = 80) -> str:
        """Reads live status and log output of a managed workspace application."""
        res = get_process_registry().get_logs(run_id.strip(), offset=0, tail_lines=tail_lines)
        if not res.get("ok"):
            logger.debug(f"[EXECUTOR] get_app_logs miss run_id={run_id}: {res.get('error')}")
            return f"[EXECUTOR] {res.get('error', 'Log lookup failed.')}"
        logger.debug(f"[EXECUTOR] get_app_logs run_id={res['run_id']} status={res['status']} bytes={len(res.get('chunk') or '')}")
        resolved_note = f" (resolved from '{res['resolved_from']}')" if res.get("resolved_from") else ""
        header = f"[EXECUTOR] run_id={res['run_id']}{resolved_note} | status={res['status']} | exit_code={res.get('exit_code')}"
        urls = res.get("detected_urls") or []
        if urls:
            header += " | URL=" + ", ".join(urls)
        chunk = (res.get("chunk") or "").strip() or "(no log output yet)"
        return f"{header}\n{chunk}"

    def list_running_apps(self) -> str:
        """Lists all active and recent workspace runs, including orphaned OS processes."""
        ws_dir = self._resolve_workspace_dir()
        runs = get_process_registry().list_all_processes(workspace_dir=ws_dir)
        if not runs:
            return "[EXECUTOR] No managed or orphaned workspace processes running."
        lines = ["Workspace Processes (managed + OS):"]
        for r in runs[:25]:
            urls = f" | URLs: {', '.join(r['detected_urls'])}" if r.get("detected_urls") else ""
            src_tag = "ORPHAN_OS" if r.get("source") == "orphan_os" else "managed"
            lines.append(
                f"- {r['run_id']} | {r['name']} | {src_tag} | status={r['status']} | PID={r['pid']} | exit={r.get('exit_code')}{urls}"
            )
        return "\n".join(lines)

    def stop_app(self, run_id: str) -> str:
        """
        Stops a running workspace application by run_id, OS PID (e.g. '38300' or 'os_38300'),
        project folder/name (e.g. 'task_studio'), or 'all'.
        """
        token = (run_id or "").strip()
        if not token:
            return "[EXECUTOR] Provide a run_id, PID, project path/name, or 'all'."
        ws_dir = self._resolve_workspace_dir()
        reg = get_process_registry()

        if token.lower() == "all":
            res = reg.stop_all_runs(include_orphans=True, workspace_dir=ws_dir)
            return f"[EXECUTOR] Stopped all workspace processes (count={res.get('stopped_count', 0)})."

        if token.lower().startswith(("pid:", "os_")):
            raw_pid = token.split(":", 1)[1] if ":" in token else token[3:]
            if raw_pid.isdigit():
                res = reg.stop_pid(int(raw_pid), workspace_dir=ws_dir)
                return f"[EXECUTOR] {res.get('message') or res.get('error', 'Failed.')}"

        if token.isdigit():
            res = reg.stop_pid(int(token), workspace_dir=ws_dir)
            return f"[EXECUTOR] {res.get('message') or res.get('error', 'Failed.')}"

        # Try run_id first; fall back to stopping by workspace path/project folder name
        if any(r.get("run_id") == token for r in reg.list_runs()):
            res = reg.stop_run(token)
            if not res.get("ok"):
                return f"[EXECUTOR] {res.get('error', 'Failed to stop process.')}"
            return f"[EXECUTOR] {res.get('message', 'Stopped.')} (status={res.get('status')})"

        return self.stop_project_processes(token)

    def stop_project_processes(self, target_path: str) -> str:
        """Stops all managed and orphaned OS processes locking a workspace project or file."""
        ws_dir = self._resolve_workspace_dir()
        raw = (target_path or "").strip()
        if not raw:
            return "[EXECUTOR] Missing target_path."
        abs_target, _ = resolve_authorized_target(raw, ws_dir, strict_workspace_only=False)
        target = abs_target or (raw if os.path.isabs(raw) else os.path.join(ws_dir, raw))
        res = get_process_registry().stop_by_path(target, workspace_dir=ws_dir)
        return (
            f"[EXECUTOR] Stopped {res.get('stopped_count', 0)} process(es) for {target} "
            f"(PIDs={res.get('stopped_pids') or []})."
        )

    def open_coding_cli(self, target_path: str = "", mode: str = "aider") -> str:
        """
        Opens a native Windows coding CLI window for a workspace project:
        - mode='aider': Interactive Aider CLI connected to Hecos's active LLM/Ollama settings
        - mode='shell': PowerShell in the project folder with python_env & aider_env on PATH
        - mode='trace': Live Coding Action Trace console
        """
        from .cli_bridge.terminal_launcher import launch_native_terminal

        ws_dir = self._resolve_workspace_dir()
        raw = (target_path or "").strip()
        resolved = ws_dir
        if raw:
            abs_t, _ = resolve_authorized_target(raw, ws_dir, strict_workspace_only=False)
            resolved = abs_t or (raw if os.path.isabs(raw) else os.path.join(ws_dir, raw))
        res = launch_native_terminal(mode=mode, target_path=resolved, workspace_dir=ws_dir)
        if not res.get("ok"):
            return f"[EXECUTOR] {res.get('error', 'Failed to open coding CLI.')}"
        return f"[EXECUTOR] Opened {res.get('title')} in {res.get('cwd')}."

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
            "read_file": "Read a file's content with line numbers and safe pagination.",
            "write_file": "Write or create a file (overwrite or append).",
            "patch_file": "Surgically replace a unique text block inside a file.",
            "move_path": "Move or rename a file or folder.",
            "delete_file": "Delete a file.",
            "create_dir": "Create a directory tree.",
            "list_dir": "List a directory's contents.",
            "set_important_path": "Memorize an important directory path for the user (e.g., user_profile, downloads).",
            "get_important_paths": "Get all important paths memorized by the user, and the default workspace.",
            "project_tree": "Display a compact directory tree for a project or module.",
            "repo_map": "Generate an AST repository map (files, classes, functions, line numbers).",
            "search_code": "AST-aware code search (grep-ast) across project files.",
            "check_syntax": "Validate Python (AST+Ruff), JSON, YAML, JS/TS, CSS, or HTML syntax.",
            "run_project_test": "Run a Python script, unittest, or pytest suite inside an authorized workspace/project.",
            "git_status": "Check Git branch and modified/untracked files.",
            "git_diff": "View unified Git diff for a repository or file.",
            "git_checkpoint": "Save a non-destructive Git checkpoint snapshot.",
            "git_restore": "Restore a file or tree from HEAD or a saved Git checkpoint.",
            "run_aider_task": "Delegate multi-file coding edits to isolated Aider CLI (if installed).",
            "start_app": "Start a persistent workspace script, local web server, or desktop GUI app with managed logging.",
            "probe_url": "Verify a local HTTP URL and referenced static CSS/JS assets return 200 OK.",
            "get_app_logs": "Read status and live log output for a managed workspace app by run_id.",
            "list_running_apps": "List active and recent managed workspace applications.",
            "stop_app": "Stop a running managed workspace application by run_id.",
        }
    }

def status():
    return tools.status

def get_plugin():
    return tools


