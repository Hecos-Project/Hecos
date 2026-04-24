"""
MODULO: UI Updater - Zentra Core
DESCRIZIONE: Aggiorna la riga della dashboard hardware in-place ogni 2 secondi,
             senza flickering e senza interferire con l'input utente.
"""

import sys
import os
import time
import threading
import re
from colorama import Fore, Style
from zentra.ui import graphics
from zentra.core.system import module_loader
from zentra.ui.interface import get_hardware_row

_config_ref     = None
_state_ref      = None
_dashboard_mod  = None
_updater_active = False
_updater_thread = None
_cached_L       = 115

# Global block to protect simultaneous stdout access
stdout_lock = threading.Lock()

def get_cached_L():
    global _cached_L
    return _cached_L

def update_cached_L():
    global _cached_L
    try:
        import shutil
        _cached_L = max(90, shutil.get_terminal_size((115, 30)).columns - 1)
    except:
        pass
    return _cached_L

# --- Win32 API per il cursore (già presente nel tuo file, lo manteniamo)
if os.name == 'nt':
    import ctypes
    from ctypes import wintypes
    kernel32 = ctypes.windll.kernel32
    STD_OUTPUT_HANDLE = -11
    class COORD(ctypes.Structure):
        _fields_ = [("X", wintypes.SHORT), ("Y", wintypes.SHORT)]
    class SMALL_RECT(ctypes.Structure):
        _fields_ = [("Left", wintypes.SHORT), ("Top", wintypes.SHORT),
                    ("Right", wintypes.SHORT), ("Bottom", wintypes.SHORT)]
    class CONSOLE_SCREEN_BUFFER_INFO(ctypes.Structure):
        _fields_ = [("dwSize", COORD),
                    ("dwCursorPosition", COORD),
                    ("wAttributes", wintypes.WORD),
                    ("srWindow", SMALL_RECT),
                    ("dwMaximumWindowSize", COORD)]

def is_viewport_at_bottom():
    """
    Checks if the terminal viewport is currently at the bottom of the buffer.
    If the user has scrolled up to read history, this returns False.
    """
    if os.name != 'nt':
        return True # Fallback for non-Windows (complex to detect scroll without libs)
        
    try:
        handle = kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
        csbi = CONSOLE_SCREEN_BUFFER_INFO()
        if kernel32.GetConsoleScreenBufferInfo(handle, ctypes.byref(csbi)):
            # srWindow.Bottom is the zero-based index of the last visible row.
            # dwCursorPosition.Y is where the next char will be written (usually the bottom).
            # We allow 2 lines of margin for variations in prompt rendering.
            return csbi.srWindow.Bottom >= csbi.dwCursorPosition.Y - 2
    except:
        pass
    return True

def _update_title_bar(row_text):
    """Updates the terminal window title with just the app name and status guide."""
    try:
        # Keep title clean and simple as requested
        title = "Zentra Core"
        if os.name == 'nt':
            ctypes.windll.kernel32.SetConsoleTitleW(title)
        else:
            sys.stdout.write(f"\033]2;{title}\007")
            sys.stdout.flush()
    except:
        pass

def _update_dashboard_os(text, row_index):
    """
    Intelligent Console Update using ANSI and Win32 fallback.
    """
    if os.name == 'nt':
        try:
            handle = kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
            csbi = CONSOLE_SCREEN_BUFFER_INFO()
            if kernel32.GetConsoleScreenBufferInfo(handle, ctypes.byref(csbi)):
                # Only update if the row is still within the visible buffer to avoid jumps
                view_height = csbi.srWindow.Bottom - csbi.srWindow.Top
                if csbi.dwCursorPosition.Y - csbi.srWindow.Top < view_height:
                    old_pos = csbi.dwCursorPosition
                    target_pos = COORD(0, row_index - 1)
                    kernel32.SetConsoleCursorPosition(handle, target_pos)
                    sys.stdout.write(text.rstrip() + "\033[K")
                    sys.stdout.flush()
                    kernel32.SetConsoleCursorPosition(handle, old_pos)
                    return
        except: pass

    # Generic ANSI fallback (Safe, but might flicker on some terminals)
    sys.stdout.write(f"\0337\033[{row_index};1H\033[K{text}\033[0m\0338")
    sys.stdout.flush()

def _update_cycle(interval: float):
    global _updater_active
    while _updater_active:
        row = get_hardware_row(config=None, dashboard_mod=_dashboard_mod)
        if _updater_active:
            with stdout_lock:
                # 1. Update title bar (Clean)
                _update_title_bar("")
                
                # RESTORED: Update dashboard in Row 4 of the screen
                _update_dashboard_os(row, 4)
        
        # Wait in small intervals to allow prompt termination
        for _ in range(int(interval * 10)):
            if not _updater_active:
                break
            time.sleep(0.1)

def start(config_manager, state_manager, dashboard_module, interval: float = 2.0):
    global _config_ref, _state_ref, _dashboard_mod, _updater_active, _updater_thread
    if _updater_active:
        return
    _config_ref    = config_manager
    _state_ref     = state_manager
    _dashboard_mod = dashboard_module
    _updater_active = True
    _updater_thread = threading.Thread(target=_update_cycle, args=(interval,), daemon=True, name="ZentraUIUpdater")
    _updater_thread.start()

def stop():
    global _updater_active, _updater_thread
    _updater_active = False
    if _updater_thread and _updater_thread.is_alive() and _updater_thread is not threading.current_thread():
# Wait a bit longer to be sure the dashboard thread kills itself completely 
# before opening panels like F7. This was causing a graphical glitch.
        _updater_thread.join(timeout=1.0)
    _updater_thread = None