"""
MODULO: UI Updater - Aura Core
DESCRIZIONE: Aggiorna la riga della dashboard hardware in-place ogni 2 secondi,
             senza flickering e senza interferire con l'input utente.

FISSA SU WINDOWS: Utilizza le API Win32 (ctypes) per salvare e ripristinare in
modo assoluto e garantito la posizione del cursore, superando i limiti di 
Colorama nell'elaborazione delle sequenze ANSI Save/Restore (s, u) su terminali legacy.
"""

import sys
import os
import time
import threading
import re
from colorama import Fore, Style
from ui import grafica

# ─────────────────────────────────────────────
#  Lock CONDIVISO su stdout
#  Importalo negli altri moduli per scritture sicure
# ─────────────────────────────────────────────
stdout_lock = threading.Lock()

DASHBOARD_ROW = 3
_L = 90
_COMPENSAZIONE = 60

_config_ref     = None
_state_ref      = None
_dashboard_mod  = None
_updater_attivo = False
_updater_thread = None

# ─────────────────────────────────────────────
#  Integrazione Win32 API per il Cursore 
# ─────────────────────────────────────────────
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
        
        # 1. Recupera Info Console e salva posizione cursore attuale
        kernel32.GetConsoleScreenBufferInfo(hConsole, ctypes.byref(csbi))
        saved_pos = csbi.dwCursorPosition
        
        # 2. Coordinate assolute (Y = scroll_window_top + offset)
        target_y = csbi.srWindow.Top + (riga_index - 1)
        
        # 3. Sposta cursore alla riga hardware (X=0)
        kernel32.SetConsoleCursorPosition(hConsole, COORD(0, target_y))
        
        # 4. Scrivi la nuova riga sovrascrivendola (\033[2K cancella visibilmente)
        # Sovrascriviamo con riempimento spazi in coda di sicurezza per Win Legacy
        sys.stdout.write(f"\033[2K{riga_formattata}\r")
        sys.stdout.flush()
        
        # 5. RIPRISTINA la posizione originaria (garantito al 100% da Win32)
        kernel32.SetConsoleCursorPosition(hConsole, saved_pos)

else:
    # Linux / MacOS fallback (Usa le sequenze classiche DEC Save/Restore)
    def _aggiorna_dashboard_os(riga_formattata, riga_index):
        sys.stdout.write(
            f"\0337"                           # DEC Save
            f"\033[{riga_index};1H"            # vai a riga_index
            f"\033[2K"                         # cancella l'intera riga
            f"{riga_formattata}"               # stampa i nuovi dati
            f"\0338"                           # DEC Restore
        )
        sys.stdout.flush()


# ─────────────────────────────────────────────
#  Core
# ─────────────────────────────────────────────
def _aggiorna_riga_hardware():
    try:
        stats = _dashboard_mod.get_stats()
        cpu  = stats['cpu']
        ram  = stats['ram']
        vram = stats['vram']
        backend_status = stats['backend_status']

        barra_cpu = grafica.crea_barra(cpu, larghezza=12)
        barra_ram = grafica.crea_barra(ram, larghezza=12)

        if backend_status == "PRONTA":
            stato_colore = Fore.GREEN
        elif backend_status in ("OFFLINE", "ERRORE", "TIMEOUT"):
            stato_colore = Fore.RED
        else:
            stato_colore = Fore.YELLOW

        info_hw = (
            f" CPU: {barra_cpu}  RAM: {barra_ram}  "
            f"VRAM: {vram}  {stato_colore}BACKEND: {backend_status}{Fore.CYAN} "
        )
        
        # Calcola lunghezza visibile effettiva senza codici ANSI
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        l_vis = len(ansi_escape.sub('', info_hw))
        
        spazio_rimanente = max(0, _L - l_vis)
        pad_left = spazio_rimanente // 2
        pad_right = spazio_rimanente - pad_left
        
        riga_formattata = f"{Fore.CYAN}{' ' * pad_left}{info_hw}{' ' * pad_right}{Style.RESET_ALL}"

    except Exception:
        riga_formattata = f"{Fore.RED}{'-- ERRORE TELEMETRIA --'.center(_L)}{Style.RESET_ALL}"

    # Stampa in lock bypassando il buffering intermedio colorama-curses
    with stdout_lock:
        _aggiorna_dashboard_os(riga_formattata, DASHBOARD_ROW)


def _ciclo_aggiornamento(intervallo: float):
    global _updater_attivo
    while _updater_attivo:
        _aggiorna_riga_hardware()
        for _ in range(int(intervallo * 10)):
            if not _updater_attivo:
                break
            time.sleep(0.1)


def avvia(config_manager, state_manager, dashboard_module, intervallo: float = 2.0):
    global _config_ref, _state_ref, _dashboard_mod
    global _updater_attivo, _updater_thread

    if _updater_attivo:
        return

    _config_ref    = config_manager
    _state_ref     = state_manager
    _dashboard_mod = dashboard_module
    _updater_attivo = True

    _updater_thread = threading.Thread(
        target=_ciclo_aggiornamento,
        args=(intervallo,),
        daemon=True,
        name="AuraUIUpdater"
    )
    _updater_thread.start()

def ferma():
    global _updater_attivo
    _updater_attivo = False
