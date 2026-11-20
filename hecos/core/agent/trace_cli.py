"""
hecos/core/agent/trace_cli.py
Terminal CLI renderer for the Agent Trace system.
Provides colorized progress messages and box-drawing action windows with Windows console encoding protection.
"""

import sys
from typing import Optional
from hecos.core.logging import logger

# ANSI Colors for Terminal
COLOR_AGENT = "\033[96m"    # Cyan
COLOR_TOOL = "\033[93m"     # Yellow
COLOR_ERROR = "\033[91m"    # Red
COLOR_SUCCESS = "\033[92m"  # Green
COLOR_RESET = "\033[0m"


def safe_print(text: str) -> None:
    """Prints to stdout without raising UnicodeEncodeError on Windows cp1252 consoles."""
    try:
        print(text)
    except UnicodeEncodeError:
        try:
            enc = getattr(sys.stdout, "encoding", None) or "utf-8"
            safe_bytes = text.encode(enc, errors="replace")
            print(safe_bytes.decode(enc, errors="replace"))
        except Exception:
            pass
    except Exception:
        pass


def print_cli_trace(msg: str, level: str = "info", cli_enabled: bool = True) -> None:
    """Outputs a formatted trace step to the terminal if CLI traces are enabled."""
    if not cli_enabled:
        return

    color = COLOR_AGENT
    prefix = "🧠 [Agent]"
    if level == "tool":
        color = COLOR_TOOL
        prefix = "⚡ [Tool]"
    elif level == "error":
        color = COLOR_ERROR
        prefix = "❌ [Error]"
    elif level == "success":
        color = COLOR_SUCCESS
        prefix = "✅ [Done]"

    safe_print(f"{color}{prefix} {msg}{COLOR_RESET}")
    logger.debug("AGENT_TRACE", f"{level.upper()}: {msg}")


def print_cli_action_box(tool_name: str, command: str, preview: str, cli_enabled: bool = True) -> None:
    """Renders a box-drawing action console window to the terminal."""
    if not cli_enabled:
        return

    safe_print(f"\n{COLOR_TOOL}┌── [ACTION] {tool_name}{COLOR_RESET}")
    safe_print(f"{COLOR_AGENT}│ $ {command}{COLOR_RESET}")
    for line in preview.splitlines():
        safe_print(f"│   {line}")
    safe_print(f"{COLOR_TOOL}└─────────────────────{COLOR_RESET}\n")

