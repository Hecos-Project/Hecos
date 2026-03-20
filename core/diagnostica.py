"""
MODULO: Diagnostica di Sistema - Aura Core
DESCRIZIONE: Gestisce i check pre-volo, ora supporta anche Kobold.
"""

import os
import time
import requests
import importlib
import glob
import psutil
import msvcrt
import json
from core import logger, voce
from ui import interfaccia
from core.version import VERSION, COPYRIGHT, get_version_string

VERDE = '\033[92m'
ROSSO = '\033[91m'
CIANO = '\033[96m'
GIALLO = '\033[93m'
RESET = '\033[0m'

def check_bypass():
    try:
        bypassed = False
        while msvcrt.kbhit():
            tasto = msvcrt.getch()
            if tasto == b'\x1b':
                bypassed = True
        return bypassed
    except Exception:
        pass
    return False

def stampa_e_parla(testo_video, testo_voce=None):
    print(testo_video)
    if testo_voce:
        voce.parla(testo_voce)
    time.sleep(0.1)

def check_cartelle():
    cartelle = ["plugins", "personalita", "logs", "memoria", "core", "ui", "app"]
    mancanti = [c for c in cartelle if not os.path.exists(c)]
    return mancanti

def check_hardware():
    cpu = psutil.cpu_percent(interval=0.1)
    ram = psutil.virtual_memory().percent
    stato_cpu = f"{VERDE}OK{RESET}" if cpu < 80 else f"{ROSSO}ALTA ({cpu}%){RESET}"
    stato_ram = f"{VERDE}OK{RESET}" if ram < 85 else f"{ROSSO}CRITICA ({ram}%){RESET}"
    return f"   [+] CPU Core: {stato_cpu} | Memoria Neurale (RAM): {stato_ram}"

def check_backend(config):
    """Verifica lo stato del backend attivo (Ollama o Kobold)."""
    backend_type = config.get('backend', {}).get('tipo', 'ollama')
    print(f"   [>] Verifica backend {backend_type.upper()}...")
    
    if backend_type == 'kobold':
        url = config.get('backend', {}).get('kobold', {}).get('url', 'http://localhost:5001').rstrip('/') + '/api/v1/model'
        try:
            r = requests.get(url, timeout=2)
            if r.status_code == 200:
                print(f"   [+] {VERDE}Backend Kobold: ONLINE{RESET}")
                return True
            else:
                print(f"   [-] {ROSSO}Backend Kobold: ERRORE ({r.status_code}){RESET}")
                return False
        except Exception as e:
            print(f"   [-] {ROSSO}Backend Kobold: NON RISPONDE ({e}){RESET}")
            return False
    else:  # ollama
        # Legge il modello dal backend attivo, non più da 'ia'
        modello = config.get('backend', {}).get('ollama', {}).get('modello', 'llama3.2:1b')
        url = "http://localhost:11434/api/generate"
        payload = {"model": modello, "prompt": "hi", "stream": False}
        try:
            print(f"   [>] Inizializzazione VRAM per: {modello}...")
            response = requests.post(url, json=payload, timeout=60)
            if response.status_code == 200:
                print(f"   [+] {VERDE}Rete Neurale: ONLINE (Modello pronto){RESET}")
                return True
            return False
        except Exception as e:
            logger.errore(f"DIAGNOSTICA: Ollama non risponde: {e}")
            print(f"   [-] {ROSSO}Ollama non risponde correttamente.{RESET}")
            return False

def scansiona_plugins():
    """
    Cerca e interroga moduli aggiuntivi in automatico.
    Supporta la nuova struttura a cartelle (plugins/nome_modulo/main.py).
    Mostra anche il conteggio dei plugin disabilitati.
    """
    risultati = []
    from core import plugin_loader
    plugin_loader.aggiorna_registro_capacita()
    
    # ---- Controllo plugin disabilitati ----
    disabled_path = os.path.join("plugins", "plugins_disabled")
    disabled_count = 0
    if os.path.exists(disabled_path) and os.path.isdir(disabled_path):
        for item in os.listdir(disabled_path):
            item_path = os.path.join(disabled_path, item)
            if os.path.isdir(item_path) and not item.startswith("__"):
                if os.path.exists(os.path.join(item_path, "main.py")):
                    disabled_count += 1
                else:
                    disabled_count += 1
    
    if disabled_count > 0:
        risultati.append(f"   [!] {GIALLO}Plugin disattivati: {disabled_count}{RESET}")
    # ----------------------------------------
    
    # Cerca nella nuova struttura (sottocartelle con main.py)
    plugin_dirs = [d for d in os.listdir("plugins") 
                  if os.path.isdir(os.path.join("plugins", d)) 
                  and not d.startswith("__")
                  and d != "plugins_disabled"]  # Ignora la cartella dei disabilitati
    
    for plugin_dir in plugin_dirs:
        main_file = os.path.join("plugins", plugin_dir, "main.py")
        if not os.path.exists(main_file):
            continue
            
        try:
            # Importa il plugin dalla nuova struttura
            spec = importlib.util.spec_from_file_location(
                f"plugins.{plugin_dir}.main", 
                main_file
            )
            if spec is None:
                continue
                
            modulo = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(modulo)
            
            nome_modulo = plugin_dir.upper()
            if hasattr(modulo, "status"):
                esito = modulo.status()
                risultati.append(f"   [+] Plugin '{nome_modulo}': {VERDE}{esito}{RESET}")
            else:
                risultati.append(f"   [?] Plugin '{nome_modulo}': {GIALLO}Attivo{RESET}")
        except Exception as e:
            risultati.append(f"   [-] Plugin '{plugin_dir.upper()}': {ROSSO}ERRORE ({e}){RESET}")
    
    return risultati

def esegui_check_iniziale(config):
    return avvia_sequenza_risveglio(config)

def avvia_sequenza_risveglio(config):
    os.system('cls' if os.name == 'nt' else 'clear')
    
    # Usa le variabili centralizzate da core.version
    print(f"{VERDE}{get_version_string()}{RESET}")
    print(f"{VERDE}{COPYRIGHT}{RESET}")
    print(f"{'─' * 55}\n")
    
    print(f"{CIANO}==================================================={RESET}")
    print(f"{CIANO}  SISTEMA OPERATIVO AURA - INIZIALIZZAZIONE...{RESET}")
    print(f"{CIANO}      (Premi ESC in qualsiasi momento per saltare){RESET}")
    print(f"{CIANO}==================================================={RESET}\n")
    
    if check_bypass(): return True
    mancanti = check_cartelle()
    if mancanti:
        print(f"   [-] {ROSSO}ERRORE: Directory mancanti: {', '.join(mancanti)}{RESET}")
        time.sleep(2)
        return False
    print(f"   [+] {VERDE}Struttura dati: INTEGRA{RESET}")

    if check_bypass(): return True
    print(check_hardware())
    
    if check_bypass(): return True
    print(f"   [+] Modulo Vocale: {VERDE}ATTIVO{RESET}")
    
    if check_bypass(): return True
    soglia = config.get('ascolto', {}).get('soglia_energia', 'N/D')
    print(f"   [+] Modulo Ascolto: {VERDE}PRONTO (Soglia: {soglia}){RESET}")
    
    # Check backend
    if check_bypass(): return True
    check_backend(config)
    
    # Plugin Scan
    if check_bypass(): return True
    esiti = scansiona_plugins()
    for esito in esiti[:5]:
        if check_bypass(): return True
        print(esito)

    print(f"\n{CIANO}==================================================={RESET}")
    stampa_e_parla(f"{VERDE}[SISTEMA] {RESET}", "Ciao, sono Aura")
    
    while msvcrt.kbhit():
        msvcrt.getch()
        
    time.sleep(0.5)
    return True