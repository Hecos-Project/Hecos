"""
MODULO: Monitor di Rianimazione Semplificato - Aura Core
DESCRIZIONE: Monitora solo config.json per il riavvio.
"""

import subprocess
import time
import os
import sys

# Configurazione percorsi
SCRIPT_PRINCIPALE = "main.py"
FILE_CONFIG = "config.json"

def ottieni_timestamp_file(path):
    if os.path.exists(path):
        return os.path.getmtime(path)
    return 0

def avvia_e_monitora():
    if not os.path.exists(SCRIPT_PRINCIPALE):
        print(f"[MONITOR] CRITICO: {SCRIPT_PRINCIPALE} non trovato.")
        return False

    last_config_time = ottieni_timestamp_file(FILE_CONFIG)
    print(f"[MONITOR] Avvio di Aura...")
    
    # Avvio del processo
    processo = subprocess.Popen([sys.executable, SCRIPT_PRINCIPALE])

    try:
        while processo.poll() is None:
            time.sleep(1)
            
            # Controllo unico su config.json
            current_config_time = ottieni_timestamp_file(FILE_CONFIG)
            if current_config_time > last_config_time + 1:
                print("\n[MONITOR] Modifica config.json rilevata. Terminazione in corso...")
                processo.terminate()
                # Attendiamo che il processo si chiuda davvero (max 5 secondi)
                try:
                    processo.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    processo.kill() # Forza la chiusura se non risponde
                
                print("[MONITOR] Reset completato. Riavvio tra 2 secondi...")
                time.sleep(2) # Pausa di sicurezza per far rifiatare la GPU
                return True
                    
    except Exception as e:
        print(f"[MONITOR] Errore: {e}")
        processo.kill()
    
    return True

if __name__ == "__main__":
    while True:
        successo = avvia_e_monitora()
        if not successo: break