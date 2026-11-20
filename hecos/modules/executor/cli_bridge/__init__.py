"""
hecos/modules/executor/cli_bridge/__init__.py
Modular CLI & Aider Bridge package for Hecos Coding Studio.
"""

from .action_feed import (
    clear_action_events,
    get_action_events,
    get_actions_log_path,
    record_action_event,
)
from .coding_cli_app import get_coding_cli_overview, run_interactive_aider_inline
from .direct_aider_runner import (
    get_direct_aider_task,
    start_direct_aider_task,
    stop_direct_aider_task,
)
from .routes_cli_bridge import register_cli_bridge_routes, register_ide_cli_routes
from .terminal_launcher import (
    build_coding_env,
    launch_native_terminal,
    resolve_project_cwd,
)

__all__ = [
    "build_coding_env",
    "clear_action_events",
    "get_action_events",
    "get_actions_log_path",
    "get_coding_cli_overview",
    "get_direct_aider_task",
    "launch_native_terminal",
    "record_action_event",
    "register_cli_bridge_routes",
    "register_ide_cli_routes",
    "resolve_project_cwd",
    "run_interactive_aider_inline",
    "start_direct_aider_task",
    "stop_direct_aider_task",
]
