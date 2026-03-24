"""
MODULO: Monitor di Rianimazione Semplificato - Zentra Core
DESCRIZIONE: Monitora solo config.json per il riavvio.
"""

import subprocess
import time
import os
import sys

# Configurazione percorsi
SCRIPT_PRINCIPALE = "main.py"
FILE_CONFIG = "config.json"

def get_translator():
    lang = "en"
    if os.path.exists(FILE_CONFIG):
        try:
            with open(FILE_CONFIG, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                lang = cfg.get("sistema", {}).get("lingua_sistema", "en")
        except: pass
    
    translations = {
        "it": {
            "critical_missing": "[MONITOR] CRITICO: {file} non trovato.",
            "starting": "[MONITOR] Avvio di Zentra...",
            "config_changed": "[MONITOR] Modifica config.json rilevata. Terminazione in corso...",
            "reset_complete": "[MONITOR] Reset completato. Riavvio tra 2 secondi...",
            "error": "[MONITOR] Errore: {error}"
        },
        "en": {
            "critical_missing": "[MONITOR] CRITICAL: {file} not found.",
            "starting": "[MONITOR] Starting Zentra...",
            "config_changed": "[MONITOR] config.json change detected. Terminating...",
            "reset_complete": "[MONITOR] Reset complete. Restarting in 2 seconds...",
            "error": "[MONITOR] Error: {error}"
        }
    }
    return lambda key, **kwargs: translations.get(lang, translations["en"]).get(key, key).format(**kwargs)

t = get_translator()

def ottieni_timestamp_file(path):
    if os.path.exists(path):
        return os.path.getmtime(path)
    return 0

def avvia_e_monitora():
    if not os.path.exists(SCRIPT_PRINCIPALE):
        print(t("critical_missing", file=SCRIPT_PRINCIPALE))
        return False

    last_config_time = ottieni_timestamp_file(FILE_CONFIG)
    print(t("starting"))
    
    # Avvio del processo
    processo = subprocess.Popen([sys.executable, SCRIPT_PRINCIPALE])

    try:
        while processo.poll() is None:
            time.sleep(1)
            
            # Controllo unico su config.json
            current_config_time = ottieni_timestamp_file(FILE_CONFIG)
            if current_config_time > last_config_time + 1:
                if os.path.exists(".config_saved_by_app"):
                    try: os.remove(".config_saved_by_app")
                    except: pass
                    last_config_time = current_config_time
                    continue
                    
                print(f"\n{t('config_changed')}")
                processo.terminate()
                # Attendiamo che il processo si chiuda davvero (max 5 secondi)
                try:
                    processo.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    processo.kill() # Forza la chiusura se non risponde
                
                print(t("reset_complete"))
                time.sleep(2) # Pausa di sicurezza per far rifiatare la GPU
                return True
                
        # Quando termina naturalmente:
        if processo.returncode == 42:
            return True # Riavvia su richiesta F6
        else:
            return False # Chiusura normale o errore diverso, non riavviare
                    
    except Exception as e:
        print(t("error", error=e))
        processo.kill()
    
    return False

if __name__ == "__main__":
    while True:
        successo = avvia_e_monitora()
        if not successo: break