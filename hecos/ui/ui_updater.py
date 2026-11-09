"""
MODULO: UI Updater - Hecos
DESCRIZIONE: Aggiorna la dashboard hardware (Zona 1, Righe 1-5) ogni 2 secondi
             tramite il compositor atomico TerminalViewport, senza flickering
             e senza mai spostare il cursore dalla barra di input in fondo.
"""

import sys
import os
import time
import threading
from hecos.ui.viewport import get_viewport

_config_ref     = None
_state_ref      = None
_dashboard_mod  = None
_updater_active = False
_updater_thread = None

# Shared re-entrant lock bound to TerminalViewport so all legacy callers synchronize safely
stdout_lock = get_viewport().lock


def get_cached_L():
    return get_viewport().usable_width


def get_cached_H():
    return get_viewport().rows


def update_cached_L():
    vp = get_viewport()
    vp.refresh_dimensions()
    return vp.usable_width


if os.name == 'nt':
    import ctypes
    from ctypes import wintypes
    kernel32 = ctypes.windll.kernel32
    STD_OUTPUT_HANDLE = -11

    class COORD(ctypes.Structure):
        _fields_ = [("X", wintypes.SHORT), ("Y", wintypes.SHORT)]

    class SMALL_RECT(ctypes.Structure):
        _fields_ = [
            ("Left", wintypes.SHORT),
            ("Top", wintypes.SHORT),
            ("Right", wintypes.SHORT),
            ("Bottom", wintypes.SHORT),
        ]

    class CONSOLE_SCREEN_BUFFER_INFO(ctypes.Structure):
        _fields_ = [
            ("dwSize", COORD),
            ("dwCursorPosition", COORD),
            ("wAttributes", wintypes.WORD),
            ("srWindow", SMALL_RECT),
            ("dwMaximumWindowSize", COORD),
        ]


def is_viewport_at_bottom():
    """Checks if the terminal viewport is currently at the bottom of the buffer."""
    if os.name != 'nt':
        return True
    try:
        handle = kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
        csbi = CONSOLE_SCREEN_BUFFER_INFO()
        if kernel32.GetConsoleScreenBufferInfo(handle, ctypes.byref(csbi)):
            return csbi.srWindow.Bottom >= csbi.dwCursorPosition.Y - 2
    except Exception:
        pass
    return True


def _update_title_bar(row_text=""):
    """Updates the terminal window title cleanly without polluting stdout."""
    try:
        title = "Hecos"
        if os.name == 'nt':
            ctypes.windll.kernel32.SetConsoleTitleW(title)
    except Exception:
        pass


def update_ui_in_place(icon_instance, config, state, dashboard_mod):
    """Updates TUI Header Rows 1-5 atomically through TerminalViewport."""
    from hecos.ui import terminal_renderer as renderer

    vp = get_viewport()
    if not _updater_active or not vp.is_active or vp.is_modal:
        return

    # Detect terminal resize before building width-dependent rows
    vp.check_resize()
    L = vp.usable_width

    row1 = renderer.get_header_row(L)
    row2 = renderer.get_system_menu_row(L)
    row3 = renderer.get_status_bar(
        config,
        state.voice_status,
        state.listening_status,
        state.system_status,
        L,
        ptt_status=state.push_to_talk,
    )
    row4 = renderer.get_hardware_row(config, dashboard_mod, L)
    row5 = renderer.get_ptt_hint_row(
        L,
        system_status=state.system_status,
        ptt_status=state.push_to_talk,
    )

    vp.render_header([row1, row2, row3, row4, row5])


def _update_dashboard_os(text, row_index):
    """Updates a single header row (1..5) safely via TerminalViewport."""
    get_viewport().render_header_row(row_index, text)


def _update_cycle(interval: float):
    global _updater_active
    while _updater_active:
        try:
            cfg_manager = _config_ref
            if cfg_manager and _state_ref:
                update_ui_in_place(None, cfg_manager.config, _state_ref, _dashboard_mod)

            for _ in range(int(interval * 10)):
                if not _updater_active:
                    break
                time.sleep(0.1)
        except Exception as e:
            try:
                from hecos.core.logging import logger
                logger.debug(f"UI Updater Thread Error: {e}")
            except Exception:
                pass
            time.sleep(1)


def start(config_manager, state_manager, dashboard_module, interval: float = 2.0):
    global _config_ref, _state_ref, _dashboard_mod, _updater_active, _updater_thread
    _config_ref    = config_manager
    _state_ref     = state_manager
    _dashboard_mod = dashboard_module
    if _updater_active and _updater_thread and _updater_thread.is_alive():
        return
    _updater_active = True
    _updater_thread = threading.Thread(
        target=_update_cycle,
        args=(interval,),
        daemon=True,
        name="HecosUIUpdater",
    )
    _updater_thread.start()


def stop():
    global _updater_active, _updater_thread
    _updater_active = False
    if (
        _updater_thread
        and _updater_thread.is_alive()
        and _updater_thread is not threading.current_thread()
    ):
        _updater_thread.join(timeout=1.0)
    _updater_thread = None
