"""
hecos/modules/executor/process_runner.py
Unified facade & smart execution router for Hecos EXECUTOR and the WebUI Workspace Runner.
Re-exports modular helpers from http_probe.py, test_runner.py, and process_registry.py.
"""

from __future__ import annotations

from typing import Any, Dict

from .http_probe import (
    _is_loopback_http_url,
    _probe_single_get,
    extract_local_urls,
    probe_local_http_url,
)
from .process_registry import (
    _REGISTRY,
    ManagedProcessRegistry,
    ManagedRunEntry,
    get_process_registry,
)
from .process_watchdog import (
    discover_workspace_processes,
    safe_remove_path,
    stop_processes_for_path,
    terminate_pid_tree,
)
from .test_runner import (
    _ENTRY_PRIORITY,
    _RUNNABLE_EXTS,
    _build_bare_pytest_fallback_cmd,
    _build_python_module_cmd,
    _build_python_script_cmd,
    _build_script_invocation,
    _build_subproc_env,
    _collect_workspace_import_roots,
    _compute_discover_top_dir,
    collect_strict_workspace_roots,
    find_project_tests,
    is_test_filename,
    list_workspace_projects,
    resolve_authorized_target,
    run_tests_for_target,
)


def run_smart(
    target_path: str,
    mode: str = "auto",
    *,
    args: str = "",
    workspace_dir: str = "",
    sandbox_dir: str = "",
    timeout_seconds: int = 30,
    wait_seconds: float = 1.5,
    strict_workspace_only: bool = True,
) -> Dict[str, Any]:
    """Dispatch UI/API execution request to script, test, or managed persistent app runner."""
    clean_mode = (mode or "auto").strip().lower()
    if clean_mode == "test":
        return run_tests_for_target(
            target_path,
            workspace_dir,
            timeout_seconds=timeout_seconds,
            strict_workspace_only=strict_workspace_only,
        )
    if clean_mode == "app":
        return _REGISTRY.start_target(
            target_path,
            workspace_dir,
            sandbox_dir,
            args=args,
            wait_seconds=max(wait_seconds, 2.0),
            strict_workspace_only=strict_workspace_only,
            require_stay_alive=True,
        )
    return _REGISTRY.start_target(
        target_path,
        workspace_dir,
        sandbox_dir,
        args=args,
        wait_seconds=wait_seconds,
        strict_workspace_only=strict_workspace_only,
        require_stay_alive=False,
    )


__all__ = [
    "ManagedProcessRegistry",
    "ManagedRunEntry",
    "collect_strict_workspace_roots",
    "discover_workspace_processes",
    "extract_local_urls",
    "find_project_tests",
    "get_process_registry",
    "is_test_filename",
    "list_workspace_projects",
    "probe_local_http_url",
    "resolve_authorized_target",
    "run_smart",
    "run_tests_for_target",
    "safe_remove_path",
    "stop_processes_for_path",
    "terminate_pid_tree",
]
