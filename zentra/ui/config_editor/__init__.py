"""
Utility generiche per l'editor.
"""

import os
import sys
import msvcrt
import time
def clear_screen(first_time=False):
    """Pulisce lo schermo del terminale in-place bypassando il pesantissimo cls.
    Usa la speciale sequenza ANSI VT100 per resettare l'intero buffer visivo
    istantaneamente e riportare il cursore a 1,1.
    """
    if os.name == 'nt':
        os.system('') # Forza l'abilitazione di ANSI sui vecchi terminali cmd
    sys.stdout.write('\033[2J\033[H')
    sys.stdout.flush()

def flush_input():
    """Svuota il buffer della tastiera."""
    while msvcrt.kbhit():
        msvcrt.getch()

def get_key(timeout=None):
    """
    Legge un tasto dalla tastiera.
    Se timeout Ã¨ None, aspetta per sempre.
    Se timeout Ã¨ un numero, aspetta al massimo quei secondi.
    Restituisce il codice ASCII o None se scaduto il timeout.
    """
    start = time.time()
    while True:
        if msvcrt.kbhit():
            ch = msvcrt.getch()
            if ch == b'\x00' or ch == b'\xe0':
                ch2 = msvcrt.getch()
                return ord(ch2)
            return ord(ch)
        
        if timeout is not None and time.time() - start > timeout:
            return None
        
        time.sleep(0.01)