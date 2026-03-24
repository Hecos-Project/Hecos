"""
MODULO: Diagnostica di Sistema - Zentra Core
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
from core.logging import logger
from core.audio import voce
from ui import interface
from core.system.version import VERSION, COPYRIGHT, get_version_string
from core.i18n import translator

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
    cartelle = ["plugins", "personality", "logs", "memory", "core", "ui", "app"]
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
    print(f"   [>] Checking {backend_type.upper()} backend...")
    
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
    elif backend_type == 'cloud':
        # Per il cloud, non facciamo check di rete pesanti qui, 
        # lasciamo che sia il client a gestire l'eventuale errore di connessione/quota.
        print(f"   [+] {VERDE}Backend CLOUD: PRONTO (LiteLLM){RESET}")
        return True
    else:  # ollama
        modello = config.get('backend', {}).get('ollama', {}).get('modello', 'llama3.2:1b')
        url = "http://localhost:11434/api/generate"
        payload = {"model": modello, "prompt": "hi", "stream": False}
        try:
            print(f"   [>] Initializing VRAM for: {modello}...")
            response = requests.post(url, json=payload, timeout=60)
            if response.status_code == 200:
                print(f"   [+] {VERDE}{translator.t('diag_neural_online')}{RESET}")
                return True
            return False
        except Exception as e:
            # Se siamo su Ollama ma non risponde, è un errore. 
            # Ma se fossimo stati su Cloud, non saremmo arrivati qui.
            logger.errore(f"DIAGNOSTICA: Ollama not responding: {e}")
            print(f"   [-] {ROSSO}{translator.t('diag_ollama_error')}{RESET}")
            return False

def scansiona_plugins(config):
    """
    Cerca e interroga moduli aggiuntivi in automatico.
    Supporta il flag 'enabled' nel config.json per saltare o segnalare i plugin disattivati.
    """
    risultati = []
    from core.system import plugin_loader
    
    # Assicuriamoci che il registro sia fresco (passiamo il config)
    plugin_loader.aggiorna_registro_capacita(config)
    
    if not os.path.exists("plugins"):
        return [f"   [-] {ROSSO}Directory 'plugins' non trovata!{RESET}"]

    plugin_dirs = [d for d in os.listdir("plugins") 
                  if os.path.isdir(os.path.join("plugins", d)) 
                  and not d.startswith("__")
                  and d != "plugins_disabled"]
    
    for plugin_dir in plugin_dirs:
        main_file = os.path.join("plugins", plugin_dir, "main.py")
        if not os.path.exists(main_file):
            continue
            
        try:
            # Importa il plugin per leggerne il tag e lo stato
            spec = importlib.util.spec_from_file_location(f"diag.{plugin_dir}", main_file)
            if spec is None: continue
            modulo = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(modulo)
            
            # Recupera tag e info
            dati_info = modulo.info() if hasattr(modulo, "info") else {"tag": plugin_dir.lower()}
            tag = dati_info.get('tag', plugin_dir.lower())
            nome_display = plugin_dir.upper()
            
            # VERIFICA FLAG ENABLED NEL CONFIG
            is_enabled = config.get('plugins', {}).get(tag, {}).get('enabled', True)
            
            if is_enabled:
                if hasattr(modulo, "status"):
                    esito = modulo.status()
                    # Se l'esito è "READY" o "ATTIVO", prova a tradurlo
                    if esito in ("READY", "ATTIVO", "ONLINE"): 
                        esito = translator.t(esito.lower() if esito in ("READY", "ONLINE") else "ready")
                    elif esito in ("ERROR", "OFFLINE"):
                        esito = translator.t(esito.lower())
                    
                    risultati.append(f"   [+] Plugin '{nome_display}': {VERDE}{esito}{RESET}")
                else:
                    risultati.append(f"   [+] Plugin '{nome_display}': {VERDE}{translator.t('ready')}{RESET}")
            else:
                risultati.append(f"   [!] Plugin '{nome_display}': {GIALLO}{translator.t('disabled')}{RESET}")
                
        except Exception as e:
            risultati.append(f"   [-] Plugin '{plugin_dir.upper()}': {ROSSO}LOADING ERROR ({e}){RESET}")
    
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
    print(f"{CIANO}  {translator.t('welcome', version=VERSION)}{RESET}")
    print(f"{CIANO}  {translator.t('boot_sequence')}{RESET}")
    print(f"{CIANO}==================================================={RESET}")
    print(f"{CIANO}      (Press ESC at any time to skip){RESET}")
    print(f"{CIANO}==================================================={RESET}\n")
    
    if check_bypass(): return True
    mancanti = check_cartelle()
    if mancanti:
        print(f"   [-] {ROSSO}{translator.t('diag_error_dirs', dirs=', '.join(mancanti))}{RESET}")
        time.sleep(2)
        return False
    print(f"   [+] {VERDE}{translator.t('diag_structure_ok')}{RESET}")

    if check_bypass(): return True
    print(check_hardware())
    
    if check_bypass(): return True
    print(f"   [+] {VERDE}{translator.t('diag_voice_ok')}{RESET}")
    
    if check_bypass(): return True
    soglia = config.get('ascolto', {}).get('soglia_energia', 'N/D')
    print(f"   [+] {VERDE}{translator.t('diag_mic_ready', soglia=soglia)}{RESET}")
    
    # Check backend
    if check_bypass(): return True
    check_backend(config)
    
    # Plugin Scan
    if check_bypass(): return True
    esiti = scansiona_plugins(config)
    for esito in esiti[:5]:
        if check_bypass(): return True
        print(esito)

    print(f"\n{CIANO}==================================================={RESET}")
    
    # Estrae lingua voce (es. "en_US-lessac..." -> "en", "it_IT-paola..." -> "it")
    modello_onnx = os.path.basename(config.get("voce", {}).get("modello_onnx", "it_IT-paola-medium.onnx"))
    lingua_voce = modello_onnx.split("_")[0] if "_" in modello_onnx else "en"
    
    # Chiediamo al Translator il dizionario delle traduzioni e forziamo la lingua
    from core.i18n.translator import get_translator
    t_obj = get_translator()
    saluto_vocale = "Hello, I am Zentra" # Fallback sicuro
    try:
        # translator.translations contiene dicts della forma {'it': {...}, 'en': {...}}
        saluto_vocale = t_obj.translations.get(lingua_voce, {}).get("intro_greeting", "Hello, I am Zentra")
    except Exception:
        pass

    # Stampa in UI locale, parla in lingua VOCE
    stampa_e_parla(f"{VERDE}[SYSTEM] {RESET}" + translator.t("intro_greeting"), saluto_vocale)
    
    while msvcrt.kbhit():
        msvcrt.getch()
        
    time.sleep(0.5)
    return True