"""
hecos/ui/terminal_spinner.py
Provides background animated thinking/loading indicators inside Zone 3 (Footer)
via TerminalViewport without clobbering the conversation body or input buffer.
"""

import threading
import time
from typing import Optional

from colorama import Fore, Style
from hecos.core.i18n import translator
from hecos.ui.viewport import get_viewport

YELLOW = Fore.YELLOW
RESET = Style.RESET_ALL

# Global variable for animation control
animation_active = False
_thinking_thread: Optional[threading.Thread] = None


def _dots_cycle() -> None:
    """Renders an animated thinking status bar inside Zone 3 (Footer) via TerminalViewport."""
    global animation_active
    vp = get_viewport()
    frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    idx = 0
    try:
        stop_hint = translator.t("press_esc_to_stop")
    except Exception:
        stop_hint = "Press ESC to stop"

    while animation_active:
        frame = frames[idx % len(frames)]
        vp.set_footer_override(
            f" {YELLOW}{frame}{RESET} \033[90m[{stop_hint}]\033[0m",
            show_cursor=False,
        )
        idx += 1
        time.sleep(0.12)


def start_thinking() -> None:
    """Launches the non-intrusive Zone 3 thinking animation in a separate thread."""
    global animation_active, _thinking_thread
    if not animation_active:
        animation_active = True
        _thinking_thread = threading.Thread(
            target=_dots_cycle, daemon=True, name="HecosThinkingAnim"
        )
        _thinking_thread.start()


def stop_thinking() -> None:
    """Stops the thinking animation cleanly and restores the Zone 3 footer."""
    global animation_active, _thinking_thread
    animation_active = False
    if (
        _thinking_thread
        and _thinking_thread.is_alive()
        and _thinking_thread is not threading.current_thread()
    ):
        _thinking_thread.join(timeout=0.3)
    _thinking_thread = None
    get_viewport().set_footer_override(None)

