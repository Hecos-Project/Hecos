"""
MODULE: System Diagnostics - Hecos
DESCRIPTION: Handles pre-flight checks and hardware status.
"""

import os
import time
import threading
import importlib
import glob
import psutil
import msvcrt
import json
from hecos.core.logging import logger
from hecos.core.audio import voice
from hecos.ui import interface
from hecos.core.system.version import VERSION, COPYRIGHT, get_version_string
from hecos.core.i18n import translator
from hecos.core.constants import LOGS_DIR, SNAPSHOTS_DIR, HECOS_DIR

VERDE = '\033[92m'
ROSSO = '\033[91m'
CIANO = '\033[96m'
GIALLO = '\033[93m'
RESET = '\033[0m'
BOLD  = '\033[1m'

# Tracks when the boot sequence started (set in start_wake_sequence)
_BOOT_START_TIME: float = 0.0

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
    # Directories that should be in the user workspace (inside hecos/)
    user_folders = [LOGS_DIR, SNAPSHOTS_DIR, os.path.join(HECOS_DIR, "memory"), os.path.join(HECOS_DIR, "personality")]
    
    missing = []
    for f in package_folders:
        # Check if they exist inside hecos/ (relative to root)
        if not os.path.exists(os.path.join(HECOS_DIR, f)):
            missing.append(f"hecos/{f}")
            
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

def check_backend_async(config):
    """
    Verifies the status of the active backend in a background thread.
    Controlled by system.check_local_backend_on_boot in system.yaml.
    If set to false (default), skips the check entirely.
    """
    check_enabled = config.get('system', {}).get('check_local_backend_on_boot', False)
    if not check_enabled:
        logger.debug("[DIAG] Backend check skipped (check_local_backend_on_boot=false).")
        return

    backend_type = config.get('backend', {}).get('type', 'ollama')
    # Only run the check for local backends that require a running server
    if backend_type not in ('ollama', 'kobold'):
        logger.debug(f"[DIAG] Backend check skipped for cloud backend '{backend_type}'.")
        return

    def _run_check():
        import urllib.request, urllib.error
        probe_timeout = config.get('backend', {}).get('ollama', {}).get('probe_timeout_sec', 3)
        try:
            if backend_type == 'kobold':
                url = config.get('backend', {}).get('kobold', {}).get('url', 'http://localhost:5001').rstrip('/') + '/api/v1/model'
                try:
                    urllib.request.urlopen(url, timeout=probe_timeout)
                    logger.info(f"[DIAG] Kobold backend: ONLINE")
                except Exception as e:
                    logger.warning(f"[DIAG] Kobold backend not responding: {e}")
            else:  # ollama
                ollama_base = config.get('backend', {}).get('ollama', {}).get('url', 'http://localhost:11434').rstrip('/')
                tags_url = ollama_base + '/api/tags'
                try:
                    urllib.request.urlopen(tags_url, timeout=probe_timeout)
                    logger.info(f"[DIAG] Ollama backend: ONLINE ({ollama_base})")
                except Exception as e:
                    logger.warning(f"[DIAG] Ollama backend not responding at {ollama_base}: {e}")
        except Exception as e:
            logger.warning(f"[DIAG] Backend check error: {e}")

    t = threading.Thread(target=_run_check, daemon=True, name="HecosBackendCheck")
    t.start()
    logger.debug("[DIAG] Backend check started asynchronously.")

def scan_plugins_fast(config):
    """
    Fast plugin status scan: reads the already-built capability registry JSON
    instead of re-importing all plugin modules from scratch (which is what the
    old scan_plugins() did and was the main cause of slow boot).
    """
    from hecos.core.system.module_state import REGISTRY_PATH
    results = []
    try:
        if not os.path.isfile(REGISTRY_PATH):
            return [f"   [-] {ROSSO}Registry file not found — run module_loader first.{RESET}"]
        with open(REGISTRY_PATH, 'r', encoding='utf-8') as f:
            registry = json.load(f)
        for tag, info in registry.items():
            status = info.get('status', 'ONLINE')
            if 'DORMANT' in status or status == 'ONLINE':
                results.append(f"   [+] {tag}: {VERDE}{status}{RESET}")
            elif status in ('OFFLINE', 'ERROR'):
                results.append(f"   [-] {tag}: {ROSSO}{status}{RESET}")
            else:
                results.append(f"   [!] {tag}: {GIALLO}{status}{RESET}")
    except Exception as e:
        results.append(f"   [-] {ROSSO}Could not read registry: {e}{RESET}")
    return results


def run_initial_check(config):
    return start_wake_sequence(config)


def start_wake_sequence(config):
    global _BOOT_START_TIME
    _BOOT_START_TIME = time.time()
    _ts = time.strftime("%d/%m/%Y %H:%M:%S")

    os.system('cls' if os.name == 'nt' else 'clear')

    # ── Boot Banner ──────────────────────────────────────────────────────────
    print(f"{CIANO}{BOLD}")
    print(f"╔══════════════════════════════════════════════════════╗")
    print(f"║   🚀 HECOS AVVIO  —  {_ts:<31}║")
    print(f"║   {get_version_string():<51}║")
    print(f"╚══════════════════════════════════════════════════════╝{RESET}")
    print()
    logger.info(f"[BOOT] === HECOS AVVIO [{_ts}] ===")
    # ─────────────────────────────────────────────────────────────────────────

    print(f"{CIANO}{COPYRIGHT}{RESET}")
    print(f"{CIANO}{'─' * 55}{RESET}\n")

    print(f"{CIANO}==================================================={RESET}")
    print(f"{CIANO}  {translator.t('welcome', version=VERSION)}{RESET}")
    print(f"{CIANO}  {translator.t('boot_sequence')}{RESET}")
    print(f"{CIANO}==================================================={RESET}")
    print(f"{CIANO}      (Press ESC at any time to skip){RESET}")
    print(f"{CIANO}==================================================={RESET}\n")

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

        # Backend check — async, non-blocking, skipped for cloud backends
        check_backend_async(config)

        # Plugin Scan — FAST: reads registry JSON, does NOT re-import modules
        if check_bypass(): return True
        results = scan_plugins_fast(config)
        for res in results[:5]:
            if check_bypass(): return True
            print(res)

        print(f"\n{CIANO}==================================================={RESET}")

    from hecos.core.system.greeting import get_spoken_greeting, get_ui_greeting
    intro_greeting_voc = get_spoken_greeting(config)
    intro_greeting_ui = get_ui_greeting(config)

    print_and_speak(f"{CIANO}[SYSTEM] {RESET}" + intro_greeting_ui, intro_greeting_voc)

    while msvcrt.kbhit():
        msvcrt.getch()

    elapsed = time.time() - _BOOT_START_TIME
    logger.info(f"[BOOT] === Hecos pronto in {elapsed:.1f}s ===")
    print(f"{CIANO}{'─' * 55}{RESET}")
    print(f"{CIANO}   ✅ Hecos pronto in {elapsed:.1f}s{RESET}")
    print(f"{CIANO}{'─' * 55}{RESET}")

    time.sleep(0.5)
    return True