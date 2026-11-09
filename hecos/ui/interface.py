"""
MODULO: Interface & UI - Hecos
DESCRIZIONE: Gestisce la UI del terminale, le dashboard hardware e i tasti funzione
             appoggiandosi al motore nativo a 3 zone `TerminalViewport`.

File orchestratore per retrocompatibilità.
Implementazioni in:
- viewport.py
- terminal_renderer.py
- terminal_input.py
- terminal_menus.py
"""
import sys
import os

from hecos.ui.viewport import get_viewport, enable_native_vt_console

# Enable native UTF-8 + VT100 processing on Windows WITHOUT Colorama's legacy Win32 converter
enable_native_vt_console()

# Facade for terminal_renderer.py
from hecos.ui.terminal_renderer import (
    translate_status,
    get_status_color,
    get_header_row,
    get_system_menu_row,
    get_status_bar,
    get_ptt_hint_row,
    get_hardware_row,
    show_web_access_info,
)

# Facade for terminal_input.py
from hecos.ui.terminal_input import (
    set_active_prompt,
    print_scrolling,
    write_hecos,
    read_keyboard_input,
    push_cli_history,
)

# Facade for terminal_spinner.py
from hecos.ui.terminal_spinner import (
    start_thinking,
    stop_thinking,
    _dots_cycle,
)

# Facade for help_screen.py
from hecos.ui.help_screen import show_help

# Facade for terminal_menus.py
from hecos.ui.terminal_menus import (
    list_personalities,
    show_soul_menu,
    show_personality_menu,
    show_models_menu,
)


def enter_modal():
    """Suspends 3-zone TUI for full-screen modal screens (F1, F2, F3, F7)."""
    get_viewport().enter_modal()


def exit_modal():
    """Restores 3-zone TUI and chat history after a full-screen modal screen."""
    get_viewport().exit_modal()


def setup_console(clear_history: bool = False):
    """Initializes UTF-8, native VT100 mode, stream guards, and the 3-zone viewport."""
    from hecos.ui.ui_updater import update_cached_L
    update_cached_L()
    get_viewport().setup(clear_history=clear_history)


def move_to_body():
    """No-op: Zone 2 (Body) positioning is managed automatically by TerminalViewport."""
    pass


def move_to_prompt():
    """No-op: Zone 3 (Footer/Prompt) cursor parking is managed automatically by TerminalViewport."""
    pass


def show_complete_ui(config, voice_status, listening_status, system_status="READY", ptt_status=False):
    """Draws the complete 3-zone interface (Header 1..5, scrollable Body 6..H-2, Footer H-1..H)."""
    vp = get_viewport()
    if not vp.is_active:
        vp.setup(clear_history=False)
    else:
        vp.refresh_dimensions()

    L = vp.usable_width
    rows = [
        get_header_row(L),
        get_system_menu_row(L),
        get_status_bar(config, voice_status, listening_status, system_status, L, ptt_status=ptt_status),
        get_hardware_row(config, L=L),
        get_ptt_hint_row(L, system_status=system_status, ptt_status=ptt_status),
    ]
    with vp.lock:
        vp.render_header(rows, force=False)
        vp.full_redraw()


def update_status_bar_in_place(config, voice_status, listening_status, system_status="READY", ptt_status=False):
    """Updates Header Row 3 (Status Bar) and Row 5 (PTT Hint / Recording / Divider) atomically."""
    from hecos.ui.ui_updater import _update_title_bar

    _update_title_bar("")
    vp = get_viewport()
    if not vp.is_active or vp.is_modal:
        return

    L = vp.usable_width
    row3 = get_status_bar(
        config,
        voice_status,
        listening_status,
        system_status,
        L,
        ptt_status=ptt_status,
    )
    row5 = get_ptt_hint_row(L, system_status=system_status, ptt_status=ptt_status)

    with vp.lock:
        vp.render_header_row(3, row3)
        vp.render_header_row(5, row5)
