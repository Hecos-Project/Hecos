"""
MODULE: Hecos Coder (main.py)
DESCRIPTION: Software Development, AI Coding & Workspace Runner System App for Hecos.
Provides multi-file Aider sidecar coding, Tree-sitter AST Repo Map, Git version control
checkpoints, Project Test Runner, managed Workspace process runner & watchdog, and CLI bridge.
"""

from __future__ import annotations

import os
import re

from .aider_bridge import run_aider_task_tool
from .code_intel import build_repo_map
from .dev_tools import (
    check_syntax_tool,
    inspect_web_project_issues,
    project_tree_tool,
    run_project_test_tool,
    search_code_tool,
)
from .file_manager import AgentTracer, logger, read_file_tool, sanitize_llm_path
from .git_tools import git_checkpoint_tool, git_diff_tool, git_restore_tool, git_status_tool
from .process_runner import (
    get_process_registry,
    probe_local_http_url,
    resolve_authorized_target,
    run_tests_for_target,
)


class CoderTools:
    """
    Hecos Coder — Software Development, AI Coding & Workspace Runner Suite.
    Packaged as an HPM system_app ('coder', tag 'CODER').
    """

    def __init__(self):
        self.tag = "CODER"
        self.desc = (
            "Software Development, AI Coding & Workspace Runner Suite. "
            "Provides Aider multi-file coding, AST Repo Map, Git checkpoints, "
            "Project Test Runner, Workspace process manager, and CLI bridge."
        )
        self.status = "ONLINE (Coder Suite Active)"

        self.config_schema = {
            "test_timeout_seconds": {
                "type": "int",
                "default": 30,
                "description": "Timeout in seconds for run_project_test project execution.",
            },
            "python_interpreter": {
                "type": "string",
                "default": "",
                "description": "Optional Python executable override for run_project_test (defaults to python_env\\python.exe).",
            },
            "auto_verify_syntax_on_write": {
                "type": "bool",
                "default": True,
                "description": "Automatically verify syntax after writing or patching code/config files.",
            },
            "auto_run_existing_tests_on_write": {
                "type": "bool",
                "default": True,
                "description": "Automatically run matching existing workspace unit tests after editing Python files.",
            },
            "auto_generate_unit_tests": {
                "type": "bool",
                "default": False,
                "description": "Encourage coding presets to generate companion unit tests automatically for new modules.",
            },
            "default_run_timeout_seconds": {
                "type": "int",
                "default": 30,
                "description": "Default timeout in seconds when running scripts or test suites.",
            },
            "allow_ui_script_execution": {
                "type": "bool",
                "default": True,
                "description": "Allow launching workspace scripts and tests directly from chat cards and Workspace Runner UI.",
            },
            "aider_enabled": {
                "type": "bool",
                "default": True,
                "description": "Enable invisible Aider sidecar delegation for multi-file coding tasks.",
            },
            "aider_global_preset": {
                "type": "string",
                "default": "hecos_coder",
                "description": "Default Global Preset ID used by Aider (provides model, backend, and num_ctx unless overridden).",
            },
            "aider_model": {
                "type": "string",
                "default": "",
                "description": "Optional LiteLLM/Ollama model override for Aider (empty = use Global Preset / active model).",
            },
            "aider_num_ctx": {
                "type": "int",
                "default": 0,
                "description": "Optional context window override for Ollama (0 = inherit from Global Preset or 16384 fallback).",
            },
            "aider_edit_format": {
                "type": "string",
                "default": "",
                "description": "Optional Aider edit format override (e.g. diff, whole, udiff).",
            },
            "aider_auto_lint": {
                "type": "bool",
                "default": True,
                "description": "Let Aider run automatic syntax/lint checks after editing files.",
            },
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
        hecos_pkg_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
        raw = (configured_value or "").strip()
        normalized = raw.replace("\\", "/").rstrip("/")
        if normalized in self._LEGACY_REL_PATHS:
            return os.path.normpath(os.path.join(hecos_pkg_dir, default_subpath))
        if os.path.isabs(raw):
            return os.path.abspath(raw)
        return os.path.normpath(os.path.join(hecos_pkg_dir, raw))

    def _resolve_workspace_dir(self) -> str:
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
        clean = sanitize_llm_path(path)
        if not clean:
            return self._resolve_workspace_dir()
        if os.path.isabs(clean):
            return os.path.abspath(clean)
        return os.path.abspath(os.path.join(self._resolve_workspace_dir(), clean))

    def repo_map(self, path: str = "", max_files: int = 60, max_lines: int = 160) -> str:
        """Generates a compact multi-language AST map (files, classes, functions, line numbers) for a codebase."""
        resolved = self._resolve_target_path(path) if path else self._resolve_workspace_dir()
        return build_repo_map(resolved, max_files=max_files, max_lines=max_lines)

    def git_status(self, repo_path: str = "") -> str:
        """Inspects Git branch and modified/untracked files inside a project repository."""
        resolved = self._resolve_target_path(repo_path) if repo_path else self._resolve_workspace_dir()
        return git_status_tool(resolved)

    def git_diff(self, repo_path: str = "", file_path: str = "", staged: bool = False) -> str:
        """Shows unified Git diff (size-capped) for the repository or a specific file."""
        resolved = self._resolve_target_path(repo_path) if repo_path else self._resolve_workspace_dir()
        return git_diff_tool(resolved, file_path=file_path, staged=staged)

    def git_checkpoint(self, repo_path: str = "", message: str = "hecos checkpoint") -> str:
        """Saves a non-destructive Git checkpoint snapshot (tracked + untracked files) without mutating HEAD."""
        resolved = self._resolve_target_path(repo_path) if repo_path else self._resolve_workspace_dir()
        return git_checkpoint_tool(resolved, message=message, auto_init=True)

    def git_restore(
        self,
        repo_path: str = "",
        file_path: str = "",
        target_ref: str = "HEAD",
        confirm_all: bool = False,
    ) -> str:
        """Restores a file (or the full tree when confirm_all=True) from HEAD or a saved checkpoint."""
        resolved = self._resolve_target_path(repo_path) if repo_path else self._resolve_workspace_dir()
        return git_restore_tool(resolved, file_path=file_path, target_ref=target_ref, confirm_all=confirm_all)

    def run_aider_task(self, repo_path: str, instruction: str, files: str = "", model: str = "") -> str:
        """Delegates a multi-file refactor/generation task to isolated Aider CLI (if installed)."""
        resolved = self._resolve_target_path(repo_path) if repo_path else self._resolve_workspace_dir()
        return run_aider_task_tool(resolved, instruction=instruction, files=files, model=model)

    def project_tree(self, path: str = "", max_depth: int = 3) -> str:
        """Generates a compact project folder tree."""
        resolved = self._resolve_target_path(path) if path else self._resolve_workspace_dir()
        return project_tree_tool(resolved, max_depth=max_depth, default_workspace=self._resolve_workspace_dir())

    def search_code(self, query: str, path: str = "", file_glob: str = "") -> str:
        """Searches text/code recursively inside a project or module directory."""
        resolved = self._resolve_target_path(path) if path else self._resolve_workspace_dir()
        return search_code_tool(query, path=resolved, file_glob=file_glob, default_workspace=self._resolve_workspace_dir())

    def check_syntax(self, file_path: str) -> str:
        """Checks syntax of a Python (.py), JSON (.json), YAML (.yaml/.yml), JS/TS, CSS, or HTML file on disk."""
        return check_syntax_tool(self._resolve_target_path(file_path))

    def run_project_test(self, target_path_or_command: str, cwd: str = "", timeout_seconds: int = 30) -> str:
        """Runs a real Python script, unittest, or pytest suite inside an authorized workspace/project."""
        work_dir = self._resolve_target_path(cwd) if cwd else self._resolve_workspace_dir()
        return run_project_test_tool(
            target_path_or_command=target_path_or_command,
            cwd=work_dir,
            timeout_seconds=timeout_seconds,
            default_workspace=self._resolve_workspace_dir(),
        )

    def start_app(self, target_path: str, args: str = "", wait_seconds: float = 2.5) -> str:
        """Starts a persistent workspace script, local web server, or desktop GUI app."""
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
            return f"[CODER] {res.get('error', 'Failed to start application.')}"
        lines = [
            f"[CODER] Process {res.get('status', 'unknown').upper()} | run_id={res.get('run_id')} | PID={res.get('pid')} | file={res.get('path')}",
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
        """Tests a local running web server URL and referenced static CSS/JS assets."""
        res = probe_local_http_url(url, timeout=2.5, check_assets=True, retries=2)
        AgentTracer.emit_action("probe_url", url, res.get("summary") or res.get("error", ""))
        if res.get("ok"):
            return f"[CODER] [HEALTH-CHECK OK] {res.get('url')} -> {res.get('summary')}"
        return f"[CODER] [HEALTH-CHECK FAILED] {res.get('url')} -> {res.get('summary') or res.get('error')}"

    def get_app_logs(self, run_id: str, tail_lines: int = 80) -> str:
        """Reads live status and log output of a managed workspace application."""
        res = get_process_registry().get_logs(run_id.strip(), offset=0, tail_lines=tail_lines)
        if not res.get("ok"):
            return f"[CODER] {res.get('error', 'Log lookup failed.')}"
        resolved_note = f" (resolved from '{res['resolved_from']}')" if res.get("resolved_from") else ""
        header = f"[CODER] run_id={res['run_id']}{resolved_note} | status={res['status']} | exit_code={res.get('exit_code')}"
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
            return "[CODER] No managed or orphaned workspace processes running."
        lines = ["Workspace Processes (managed + OS):"]
        for r in runs[:25]:
            urls = f" | URLs: {', '.join(r['detected_urls'])}" if r.get("detected_urls") else ""
            src_tag = "ORPHAN_OS" if r.get("source") == "orphan_os" else "managed"
            lines.append(
                f"- {r['run_id']} | {r['name']} | {src_tag} | status={r['status']} | PID={r['pid']} | exit={r.get('exit_code')}{urls}"
            )
        return "\n".join(lines)

    def stop_app(self, run_id: str) -> str:
        """Stops a running workspace application by run_id, OS PID, project folder/name, or 'all'."""
        token = (run_id or "").strip()
        if not token:
            return "[CODER] Provide a run_id, PID, project path/name, or 'all'."
        ws_dir = self._resolve_workspace_dir()
        reg = get_process_registry()

        if token.lower() == "all":
            res = reg.stop_all_runs(include_orphans=True, workspace_dir=ws_dir)
            return f"[CODER] Stopped all workspace processes (count={res.get('stopped_count', 0)})."

        if token.lower().startswith(("pid:", "os_")):
            raw_pid = token.split(":", 1)[1] if ":" in token else token[3:]
            if raw_pid.isdigit():
                res = reg.stop_pid(int(raw_pid), workspace_dir=ws_dir)
                return f"[CODER] {res.get('message') or res.get('error', 'Failed.')}"

        if token.isdigit():
            res = reg.stop_pid(int(token), workspace_dir=ws_dir)
            return f"[CODER] {res.get('message') or res.get('error', 'Failed.')}"

        if any(r.get("run_id") == token for r in reg.list_runs()):
            res = reg.stop_run(token)
            if not res.get("ok"):
                return f"[CODER] {res.get('error', 'Failed to stop process.')}"
            return f"[CODER] {res.get('message', 'Stopped.')} (status={res.get('status')})"

        return self.stop_project_processes(token)

    def stop_project_processes(self, target_path: str) -> str:
        """Stops all managed and orphaned OS processes locking a workspace project or file."""
        ws_dir = self._resolve_workspace_dir()
        raw = (target_path or "").strip()
        if not raw:
            return "[CODER] Missing target_path."
        abs_target, _ = resolve_authorized_target(raw, ws_dir, strict_workspace_only=False)
        target = abs_target or (raw if os.path.isabs(raw) else os.path.join(ws_dir, raw))
        res = get_process_registry().stop_by_path(target, workspace_dir=ws_dir)
        return (
            f"[CODER] Stopped {res.get('stopped_count', 0)} process(es) for {target} "
            f"(PIDs={res.get('stopped_pids') or []})."
        )

    def open_coding_cli(self, target_path: str = "", mode: str = "aider") -> str:
        """Opens a native Windows coding CLI window for a workspace project ('aider', 'shell', or 'trace')."""
        from .cli_bridge.terminal_launcher import launch_native_terminal

        ws_dir = self._resolve_workspace_dir()
        raw = (target_path or "").strip()
        resolved = ws_dir
        if raw:
            abs_t, _ = resolve_authorized_target(raw, ws_dir, strict_workspace_only=False)
            resolved = abs_t or (raw if os.path.isabs(raw) else os.path.join(ws_dir, raw))
        res = launch_native_terminal(mode=mode, target_path=resolved, workspace_dir=ws_dir)
        if not res.get("ok"):
            return f"[CODER] {res.get('error', 'Failed to open coding CLI.')}"
        return f"[CODER] Opened {res.get('title')} in {res.get('cwd')}."


tools = CoderTools()


def info():
    return {
        "tag": tools.tag,
        "desc": tools.desc,
        "commands": {
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
            "stop_project_processes": "Stop all managed and orphaned OS processes locking a workspace project.",
            "open_coding_cli": "Launch native Windows PowerShell, Interactive Aider CLI, or Live Action Trace console.",
        },
    }


def status():
    return tools.status


def get_plugin():
    return tools
