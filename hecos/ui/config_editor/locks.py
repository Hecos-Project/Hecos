"""
Gestione del file di lock per accesso concorrente al file di configurazione.
"""

import os
import time
from hecos.core.i18n import translator

LOCK_FILE = "config.lock"

def acquire_lock(timeout=5):
    """
    Acquisisce il lock attendendo al massimo 'timeout' secondi.
    Se il lock esiste ma è vecchio (>30 secondi), lo rimuove.
    """
    print(translator.t('debug_lock_acquire_attempt', timeout=timeout))
    start = time.time()
    
    # Controlla se esiste un lock vecchio
    if os.path.exists(LOCK_FILE):
        try:
            # Se il file esiste da più di 30 secondi, probabilmente è un residuo
            if time.time() - os.path.getmtime(LOCK_FILE) > 30:
                print(translator.t('debug_lock_removed_old'))
                os.remove(LOCK_FILE)
        except:
            pass
    
    while os.path.exists(LOCK_FILE):
        if time.time() - start > timeout:
            print(translator.t('debug_lock_timeout', timeout=timeout))
            return False
        time.sleep(0.1)
    
    print(translator.t('debug_lock_creating'))
    with open(LOCK_FILE, 'w') as f:
        f.write(str(os.getpid()))
    print(translator.t('debug_lock_acquired'))
    return True

def release_lock():
    """Rilascia il lock se presente."""
    if os.path.exists(LOCK_FILE):
        print(translator.t('debug_lock_release'))
        os.remove(LOCK_FILE)
        print(translator.t('debug_lock_released'))
    else:
        print(translator.t('debug_lock_not_present'))

def is_locked():
    """Verifica se il lock è attivo."""
    return os.path.exists(LOCK_FILE)