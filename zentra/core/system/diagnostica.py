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
from zentra.core.logging import logger
from zentra.core.audio import voice
from zentra.ui import interface
from zentra.core.system.version import VERSION, COPYRIGHT, get_version_string
from zentra.core.i18n import translator
from zentra.core.constants import LOGS_DIR, SNAPSHOTS_DIR, ZENTRA_DIR

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
    # Directories that should be inside the package
    package_folders = ["plugins", "core", "ui", "app"]
    # Directories that should be in the user workspace (inside zentra/)
    user_folders = [LOGS_DIR, SNAPSHOTS_DIR, os.path.join(ZENTRA_DIR, "memory"), os.path.join(ZENTRA_DIR, "personality")]
    
    missing = []
    for f in package_folders:
        # Check if they exist inside zentra/ (relative to root)
        if not os.path.exists(os.path.join(ZENTRA_DIR, f)):
            missing.append(f"zentra/{f}")
            
    for f_path in user_folders:
        if not os.path.exists(f_path):
            # Auto-create if missing
            try: os.makedirs(f_path, exist_ok=True)
            except: missing.append(os.path.basename(f_path))
            
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
            # Fast Check: Just verify if Ollama is alive and knows the model
            tags_url = "http://localhost:11434/api/tags"
            r_tags = requests.get(tags_url, timeout=2)
            if r_tags.status_code == 200:
                models = [m['name'] for m in r_tags.json().get('models', [])]
                if model in models or any(model in m for m in models):
                    print(f"   [+] {VERDE}{translator.t('diag_neural_online')}{RESET}")
                    return True
            
            # Fallback to the heavier check if tags fail or model not sure
            print(f"   [>] Initializing VRAM for: {model}...")
            response = requests.post(url, json=payload, timeout=5) # Reduced timeout for boot
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
    from zentra.core.system import module_loader
    
    # Ensure registry is fresh
    module_loader.update_capability_registry(config)
    
    plugins_dir = "plugins"
    if not os.path.exists(plugins_dir):
        plugins_dir = os.path.join("zentra", "plugins")

    if not os.path.exists(plugins_dir):
        return [f"   [-] {ROSSO}Directory 'plugins' not found!{RESET}"]

    plugin_dirs = [d for d in os.listdir(plugins_dir) 
                  if os.path.isdir(os.path.join(plugins_dir, d)) 
                  and not d.startswith("__")
                  and d != "plugins_disabled"]
    
    for plugin_dir in plugin_dirs:
        main_file = os.path.join(plugins_dir, plugin_dir, "main.py")
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
    
    # Use centralized variables from zentra.core.version
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
    from zentra.core.system.greeting import get_spoken_greeting, get_ui_greeting
    intro_greeting_voc = get_spoken_greeting(config)
    intro_greeting_ui = get_ui_greeting(config)
 
    # Print in UI locale, speak in VOICE language (Always at startup)
    print_and_speak(f"{VERDE}[SYSTEM] {RESET}" + intro_greeting_ui, intro_greeting_voc)
    
    while msvcrt.kbhit():
        msvcrt.getch()
        
    time.sleep(0.5)
    return True