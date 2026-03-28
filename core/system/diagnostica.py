"""
MODULE: System Diagnostics - Zentra Core
DESCRIPTION: Handles pre-flight checks and hardware status.
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
from core.audio import voice
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

def print_and_speak(video_text, voice_text=None):
    print(video_text)
    if voice_text:
        voice.speak(voice_text)
    time.sleep(0.1)

def check_folders():
    folders = ["plugins", "personality", "logs", "memory", "core", "ui", "app"]
    missing = [f for f in folders if not os.path.exists(f)]
    return missing

def check_hardware():
    cpu = psutil.cpu_percent(interval=0.1)
    ram = psutil.virtual_memory().percent
    cpu_status = f"{VERDE}OK{RESET}" if cpu < 80 else f"{ROSSO}HIGH ({cpu}%){RESET}"
    ram_status = f"{VERDE}OK{RESET}" if ram < 85 else f"{ROSSO}CRITICAL ({ram}%){RESET}"
    return f"   [+] CPU Core: {cpu_status} | Neural Memory (RAM): {ram_status}"

def check_backend(config):
    """Verifies the status of the active backend (Ollama, Kobold, or Cloud)."""
    backend_type = config.get('backend', {}).get('type', 'ollama')
    print(f"   [>] Checking {backend_type.upper()} backend...")
    
    if backend_type == 'kobold':
        url = config.get('backend', {}).get('kobold', {}).get('url', 'http://localhost:5001').rstrip('/') + '/api/v1/model'
        try:
            r = requests.get(url, timeout=2)
            if r.status_code == 200:
                print(f"   [+] {VERDE}Kobold Backend: ONLINE{RESET}")
                return True
            else:
                print(f"   [-] {ROSSO}Kobold Backend: ERROR ({r.status_code}){RESET}")
                return False
        except Exception as e:
            print(f"   [-] {ROSSO}Kobold Backend: NOT RESPONDING ({e}){RESET}")
            return False
    elif backend_type == 'cloud':
        # For cloud, we don't perform heavy network checks here, 
        # let the client handle connection/quota errors.
        print(f"   [+] {VERDE}Backend CLOUD: READY (LiteLLM){RESET}")
        return True
    else:  # ollama
        ollama_cfg = config.get('backend', {}).get('ollama', {})
        model = ollama_cfg.get('model', 'llama3.2:1b')
        url = "http://localhost:11434/api/generate"
        
        # Send the same GPU parameters used by client.py in production
        options = {}
        if ollama_cfg.get('num_gpu') is not None:
            options["num_gpu"] = int(ollama_cfg['num_gpu'])
        if ollama_cfg.get('num_ctx') is not None:
            options["num_ctx"] = int(ollama_cfg['num_ctx'])
        if ollama_cfg.get('keep_alive') is not None:
            options["keep_alive"] = ollama_cfg['keep_alive']
        
        payload = {"model": model, "prompt": "hi", "stream": False, "options": options}
        try:
            print(f"   [>] Initializing VRAM for: {model} (num_gpu={options.get('num_gpu', 'default')})...")
            response = requests.post(url, json=payload, timeout=120)
            if response.status_code == 200:
                print(f"   [+] {VERDE}{translator.t('diag_neural_online')}{RESET}")
                return True
            return False
        except Exception as e:
            logger.error(f"DIAGNOSTICS: Ollama not responding: {e}")
            print(f"   [-] {ROSSO}{translator.t('diag_ollama_error')}{RESET}")
            return False
def scan_plugins(config):
    """
    Automatically search and query additional modules.
    Supports the 'enabled' flag in config.json to skip or report disabled plugins.
    """
    results = []
    from core.system import plugin_loader
    
    # Ensure registry is fresh
    plugin_loader.update_capability_registry(config)
    
    if not os.path.exists("plugins"):
        return [f"   [-] {ROSSO}Directory 'plugins' not found!{RESET}"]

    plugin_dirs = [d for d in os.listdir("plugins") 
                  if os.path.isdir(os.path.join("plugins", d)) 
                  and not d.startswith("__")
                  and d != "plugins_disabled"]
    
    for plugin_dir in plugin_dirs:
        main_file = os.path.join("plugins", plugin_dir, "main.py")
        if not os.path.exists(main_file):
            continue
            
        try:
            # Import plugin to read tag and status
            spec = importlib.util.spec_from_file_location(f"diag.{plugin_dir}", main_file)
            if spec is None: continue
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Retrieve tag and info
            info_data = module.info() if hasattr(module, "info") else {"tag": plugin_dir.lower()}
            tag = info_data.get('tag', plugin_dir.lower())
            display_name = plugin_dir.upper()
            
            # CHECK ENABLED FLAG IN CONFIG
            is_enabled = config.get('plugins', {}).get(tag, {}).get('enabled', True)
            
            if is_enabled:
                if hasattr(module, "status"):
                    status_result = module.status()
                    # If status is "READY", "ACTIVE", or "ONLINE", try to translate it
                    if status_result in ("READY", "ACTIVE", "ONLINE"): 
                        status_result = translator.t(status_result.lower() if status_result in ("READY", "ONLINE") else "ready")
                    elif status_result in ("ERROR", "OFFLINE"):
                        status_result = translator.t(status_result.lower())
                    
                    results.append(f"   [+] Plugin '{display_name}': {VERDE}{status_result}{RESET}")
                else:
                    results.append(f"   [+] Plugin '{display_name}': {VERDE}{translator.t('ready')}{RESET}")
            else:
                results.append(f"   [!] Plugin '{display_name}': {GIALLO}{translator.t('disabled')}{RESET}")
                
        except Exception as e:
            results.append(f"   [-] Plugin '{plugin_dir.upper()}': {ROSSO}LOADING ERROR ({e}){RESET}")
    
    return results

def run_initial_check(config):
    return start_wake_sequence(config)


def start_wake_sequence(config):
    os.system('cls' if os.name == 'nt' else 'clear')
    
    # Use centralized variables from core.version
    print(f"{VERDE}{get_version_string()}{RESET}")
    print(f"{VERDE}{COPYRIGHT}{RESET}")
    print(f"{'─' * 55}\n")
    
    print(f"{CIANO}==================================================={RESET}")
    print(f"{CIANO}  {translator.t('welcome', version=VERSION)}{RESET}")
    print(f"{CIANO}  {translator.t('boot_sequence')}{RESET}")
    print(f"{CIANO}==================================================={RESET}")
    print(f"{CIANO}      (Press ESC at any time to skip){RESET}")
    print(f"{CIANO}==================================================={RESET}\n")
    
    # FAST BOOT CHECK (Set to true in config -> system -> fast_boot)
    fast_boot = config.get("system", {}).get("fast_boot", False)
    
    if check_bypass(): return True
    if not fast_boot:
        missing = check_folders()
        if missing:
            print(f"   [-] {ROSSO}{translator.t('diag_error_dirs', dirs=', '.join(missing))}{RESET}")
            time.sleep(2)
            return False
        print(f"   [+] {VERDE}{translator.t('diag_structure_ok')}{RESET}")
    
        if check_bypass(): return True
        print(check_hardware())
        
        if check_bypass(): return True
        print(f"   [+] {VERDE}{translator.t('diag_voice_ok')}{RESET}")
        
        if check_bypass(): return True
        energy_threshold = config.get('listening', {}).get('energy_threshold', 'N/D')
        print(f"   [+] {VERDE}{translator.t('diag_mic_ready', soglia=energy_threshold)}{RESET}")
        
        # Check backend
        if check_bypass(): return True
        check_backend(config)
        
        # Plugin Scan
        if check_bypass(): return True
        results = scan_plugins(config)
        for res in results[:5]:
            if check_bypass(): return True
            print(res)
    
        print(f"\n{CIANO}==================================================={RESET}")
    
    # Estrae la frase personalizzata adatta alla lingua corrente
    from core.system.greeting import get_spoken_greeting
    intro_greeting_voc = get_spoken_greeting(config)
 
    # Print in UI locale, speak in VOICE language (Always at startup)
    print_and_speak(f"{VERDE}[SYSTEM] {RESET}" + translator.t("intro_greeting"), intro_greeting_voc)
    
    while msvcrt.kbhit():
        msvcrt.getch()
        
    time.sleep(0.5)
    return True