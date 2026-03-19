"""
Gestione del file di lock per accesso concorrente al file di configurazione.
"""

import os
import time

LOCK_FILE = "config.lock"

def acquire_lock(timeout=5):
    """
    Acquisisce il lock attendendo al massimo 'timeout' secondi.
    Se il lock esiste ma è vecchio (>30 secondi), lo rimuove.
    """
    print(f"[DEBUG locks] acquire_lock() - attesa massima {timeout}s")
    start = time.time()
    
    # Controlla se esiste un lock vecchio
    if os.path.exists(LOCK_FILE):
        try:
            # Se il file esiste da più di 30 secondi, probabilmente è un residuo
            if time.time() - os.path.getmtime(LOCK_FILE) > 30:
                print("[DEBUG locks] Rimosso lock vecchio")
                os.remove(LOCK_FILE)
        except:
            pass
    
    while os.path.exists(LOCK_FILE):
        if time.time() - start > timeout:
            print(f"[DEBUG locks] TIMEOUT - lock non acquisito dopo {timeout}s")
            return False
        time.sleep(0.1)
    
    print("[DEBUG locks] Lock libero, lo creo...")
    with open(LOCK_FILE, 'w') as f:
        f.write(str(os.getpid()))
    print("[DEBUG locks] Lock acquisito")
    return True

def release_lock():
    """Rilascia il lock se presente."""
    if os.path.exists(LOCK_FILE):
        print("[DEBUG locks] Rilascio lock")
        os.remove(LOCK_FILE)
        print("[DEBUG locks] Lock rilasciato")
    else:
        print("[DEBUG locks] Lock non presente")

def is_locked():
    """Verifica se il lock è attivo."""
    return os.path.exists(LOCK_FILE)