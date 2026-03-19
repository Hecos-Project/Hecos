"""
Utility generiche per l'editor.
"""

import os
import sys
import msvcrt
import time

def clear_screen():
    """Pulisce lo schermo del terminale."""
    os.system('cls' if os.name == 'nt' else 'clear')

def flush_input():
    """Svuota il buffer della tastiera."""
    while msvcrt.kbhit():
        msvcrt.getch()

def get_key(timeout=None):
    """
    Legge un tasto dalla tastiera.
    Se timeout è None, aspetta per sempre.
    Se timeout è un numero, aspetta al massimo quei secondi.
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