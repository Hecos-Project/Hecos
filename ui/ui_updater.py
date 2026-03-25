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
from ui import graphics
from core.system import plugin_loader
from ui.interface import ottieni_riga_hardware

# Blocco globale per proteggere l'accesso simultaneo allo stdout
stdout_lock = threading.Lock()

DASHBOARD_ROW = 3
_L = 90

_config_ref     = None
_state_ref      = None
_dashboard_mod  = None
_updater_attivo = False
_updater_thread = None

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

    def _aggiorna_dashboard_os(riga_formattata, riga_index):
        hConsole = kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
        csbi = CONSOLE_SCREEN_BUFFER_INFO()
        if kernel32.GetConsoleScreenBufferInfo(hConsole, ctypes.byref(csbi)):
            saved_pos = csbi.dwCursorPosition
            
            # Con lo scrolling region attivo, la riga 3 è fissa in alto.
            target_y = riga_index - 1
            
            kernel32.SetConsoleCursorPosition(hConsole, COORD(0, target_y))
            # 2K pulisce la riga, permettendo aggiornamenti puliti
            sys.stdout.write(f"\033[2K{riga_formattata}\r")
            sys.stdout.flush()
            kernel32.SetConsoleCursorPosition(hConsole, saved_pos)
        else:
            # Fallback ANSI generico se le API Win32 falliscono
            sys.stdout.write(f"\0337\033[{riga_index};1H\033[2K{riga_formattata}\0338")
            sys.stdout.flush()
else:
    def _aggiorna_dashboard_os(riga_formattata, riga_index):
        sys.stdout.write(f"\0337\033[{riga_index};1H\033[2K{riga_formattata}\0338")
        sys.stdout.flush()

def _ciclo_aggiornamento(intervallo: float):
    global _updater_attivo
    while _updater_attivo:
        riga = ottieni_riga_hardware(config=None, dashboard_mod=_dashboard_mod)
        if _updater_attivo:  # Double check prima di scrivere a video
            with stdout_lock:
                _aggiorna_dashboard_os(riga, DASHBOARD_ROW)
        
        # Aspettiamo a intervalli piccoli per poterci interrompere tempestivamente
        for _ in range(int(intervallo * 10)):
            if not _updater_attivo:
                break
            time.sleep(0.1)

def avvia(config_manager, state_manager, dashboard_module, intervallo: float = 2.0):
    global _config_ref, _state_ref, _dashboard_mod, _updater_attivo, _updater_thread
    if _updater_attivo:
        return
    _config_ref    = config_manager
    _state_ref     = state_manager
    _dashboard_mod = dashboard_module
    _updater_attivo = True
    _updater_thread = threading.Thread(target=_ciclo_aggiornamento, args=(intervallo,), daemon=True, name="ZentraUIUpdater")
    _updater_thread.start()

def ferma():
    global _updater_attivo, _updater_thread
    _updater_attivo = False
    if _updater_thread and _updater_thread.is_alive() and _updater_thread is not threading.current_thread():
        # Diamo un lasso di tempo maggiore per essere certi che il thread della dashboard si uccida del tutto 
        # prima di aprire i pannelli come F7. E' questo che causava l'errore grafico.
        _updater_thread.join(timeout=1.0)
    _updater_thread = None