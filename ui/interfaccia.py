"""
MODULO: Interfaccia e Grafica - Zentra Core v0.6
DESCRIZIONE: Gestisce la UI del terminale, le dashboard hardware e i tasti funzione.

"Nello specifico: Disegna la barra blu di stato (modello, voce, anima) e la barra 
centrale che si collega a plugins.dashboard per i dati hardware reali. Gestisce 
inoltre l'intercettazione dei tasti funzione (F1-F6) per i menu rapidi."
"""

import os
import sys
import msvcrt
import json
import threading
import time
import glob
import requests
import psutil  # Necessario per fallback telemetria
try:
    import GPUtil  # Telemetria GPU/VRAM
except ImportError:
    GPUtil = None
from ui import grafica
from colorama import init, Fore, Back, Style
from core.system import plugin_loader, version
from core.system.version import get_version_string
from core.i18n import translator

# "Inizializzazione Colorama per colori ANSI e sfondi su Windows"
init(convert=True, autoreset=True)

# Variabile globale per controllare l'animazione
animazione_attiva = False

# "Palette colori standard"
VERDE = Fore.GREEN
GIALLO = Fore.YELLOW
ROSSO = Fore.RED
CIANO = Fore.CYAN
MAGENTA = Fore.MAGENTA
BIANCO = Fore.WHITE
RESET = Style.RESET_ALL

def setup_console():
    """ "Pulisce lo schermo e forza l'UTF-8" """
    if sys.platform == 'win32':
        os.system('chcp 65001 > nul')
    os.system('cls' if os.name == 'nt' else 'clear')

def check_ollama():
    """Verifica se il server Ollama è attivo per la barra di stato."""
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=0.2)
        return r.status_code == 200
    except:
        return False

def mostra_ui_completa(config, stato_voce, stato_ascolto, stato_sistema="PRONTA"):
    """ Disegna l'interfaccia completa: Barra Blu (Stato), Barra Hardware (placeholder) e Footer.
        La barra hardware verrà aggiornata in tempo reale da ui_updater.
    """
    setup_console()
    
    # MODIFICATO: Legge il modello dal backend attivo
    backend_type = config.get('backend', {}).get('tipo', 'ollama')
    modello = config.get('backend', {}).get(backend_type, {}).get('modello', 'N/D')
    
    anima = config.get('ia', {}).get('personalita_attiva', 'N/D').replace('.txt', '')
    mic = "ON" if stato_ascolto else "OFF"
    spk = "ON" if stato_voce else "OFF"
    
    L = 90  # Larghezza fissa per l'allineamento
    
    # 1. BARRA SUPERIORE (TITOLO) - NERO VERO
    titolo = translator.t("welcome", version=version.VERSION).center(L)
    print(f"\033[46m\033[30m{titolo}\033[0m")
    
    # 2. BARRA DI STATO DINAMICA
    mic_str = "ON" if stato_ascolto else f"{Fore.RED}OFF{Fore.WHITE}"
    mic_len = 2 if stato_ascolto else 3
    spk_str = "ON" if stato_voce else f"{Fore.RED}OFF{Fore.WHITE}"
    spk_len = 2 if stato_voce else 3
    
    info_status = translator.t("system_status", status=stato_sistema)
    
    # Calcolo lunghezza visibile per il padding (ignora i codici colore ANSI di mic/spk)
    visible_len = len(f" {info_status} | MODELLO: {modello} | ANIMA: {anima} | MIC:  | VOCE:  ") + mic_len + spk_len
    pad_left = max(0, L - visible_len) // 2
    pad_right = max(0, L - visible_len) - pad_left
    
    info_stato_colored = f" {info_status} | MODELLO: {modello} | ANIMA: {anima} | MIC: {mic_str} | VOCE: {spk_str} "
    print(f"{Back.BLUE}{Fore.WHITE}{' '*pad_left}{info_stato_colored}{' '*pad_right}{Style.RESET_ALL}")
    
    # 3. BARRA HARDWARE (PLACEHOLDER) - Verrà sovrascritta dall'updater
    # Stampiamo una riga vuota con lo stesso colore di sfondo per mantenere l'allineamento
    print(f"{Fore.CYAN}{' ' * L}{Style.RESET_ALL}")
    
    # 4. FOOTER COMANDI RAPIDI
    print(f"{Fore.CYAN}{'━' * L}{Style.RESET_ALL}")
    comandi = (
        f" {translator.t('menu_help')} | {translator.t('menu_models')} | "
        f"{translator.t('menu_persona')} | {translator.t('menu_mic')} | "
        f"{translator.t('menu_voice')} | {translator.t('menu_reboot')} | "
        f"{translator.t('menu_config')} | {translator.t('menu_exit')} "
    )
    print(f"{Style.DIM}{comandi.center(L)}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'━' * L}{Style.RESET_ALL}\n")
    
def ottieni_riga_hardware(config=None, dashboard_mod=None):
    """
    Restituisce la stringa formattata per la riga hardware (CPU, RAM, VRAM, backend).
    Garantisce una lunghezza fissa di 90 caratteri per evitare wrap e corruzione UI.
    """
    import re
    L = 90
    
    if dashboard_mod is None:
        dashboard_mod = plugin_loader.get_plugin_module("DASHBOARD")
    
    if dashboard_mod:
        try:
            stats = dashboard_mod.get_stats()
            cpu = stats['cpu']
            ram = stats['ram']
            vram = stats['vram']
            # Accorcia VRAM se troppo lunga
            if len(str(vram)) > 10: vram = str(vram)[:7] + ".."
            backend_status = stats['backend_status']
            
            barra_cpu = grafica.crea_barra(cpu, larghezza=10)
            barra_ram = grafica.crea_barra(ram, larghezza=10)
            
            # Traduci stati backend
            if backend_status == "PRONTA":
                display_status = translator.t("ready")
                stato_colore = Fore.GREEN
            elif backend_status in ("OFFLINE", "ERRORE", "TIMEOUT"):
                display_status = translator.t("disabled")
                stato_colore = Fore.RED
            else:
                display_status = backend_status
                stato_colore = Fore.YELLOW

            info_hw = translator.t("hardware_line", 
                cpu=barra_cpu, ram=barra_ram, gpu="N/D", vram=vram, 
                backend=f"{stato_colore}{display_status}{Style.RESET_ALL}"
            )
        except Exception:
            info_hw = f"{Fore.RED}-- ERRORE TELEMETRIA HARDWARE --{Style.RESET_ALL}"
    else:
        # Se il plugin è disabilitato, restituiamo una riga vuota di 90 spazi
        return f"{Fore.CYAN}{' ' * L}{Style.RESET_ALL}"
    
    # Calcolo padding per centratura perfetta a 90 caratteri
    ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
    clean = ansi_escape.sub('', info_hw)
    
    if len(clean) > L:
        # Se ancora troppo lunga (non dovrebbe capitare con i nuovi limiti), prendi i primi L caratteri visibili
        # Per sicurezza usiamo una regex che cattura sia ANSI che char per troncare correttamente
        parts = re.split(r'(\x1b\[[0-9;]*m)', info_hw)
        truncated_hw = ""
        current_len = 0
        for part in parts:
            if part.startswith('\x1b['):
                truncated_hw += part
            else:
                space_left = L - current_len
                if len(part) <= space_left:
                    truncated_hw += part
                    current_len += len(part)
                else:
                    truncated_hw += part[:space_left]
                    current_len += space_left
                    break
        return f"{Fore.CYAN}{truncated_hw}{Style.RESET_ALL}"
    
    pad_total = L - len(clean)
    pad_left = pad_total // 2
    pad_right = pad_total - pad_left
    
    return f"{Fore.CYAN}{' ' * pad_left}{info_hw}{' ' * pad_right}{Style.RESET_ALL}"

def aggiorna_barra_stato_in_place(config, stato_voce, stato_ascolto, stato_sistema="PRONTA"):
    """Aggiorna solo la riga 2 (Barra di Stato) senza pulire lo schermo."""
    from ui.ui_updater import _aggiorna_dashboard_os, stdout_lock
    from colorama import Back, Fore, Style
    
    backend_type = config.get('backend', {}).get('tipo', 'ollama')
    modello = config.get('backend', {}).get(backend_type, {}).get('modello', 'N/D')
    anima = config.get('ia', {}).get('personalita_attiva', 'N/D').replace('.txt', '')
    
    mic_str = "ON" if stato_ascolto else f"{Fore.RED}OFF{Fore.WHITE}"
    mic_len = 2 if stato_ascolto else 3
    spk_str = "ON" if stato_voce else f"{Fore.RED}OFF{Fore.WHITE}"
    spk_len = 2 if stato_voce else 3
    
    L = 90
    info_status = translator.t("system_status", status=stato_sistema)
    
    visible_len = len(f" {info_status} | MODELLO: {modello} | ANIMA: {anima} | MIC:  | VOCE:  ") + mic_len + spk_len
    pad_left = max(0, L - visible_len) // 2
    pad_right = max(0, L - visible_len) - pad_left
    
    info_stato_colored = f" {info_status} | MODELLO: {modello} | ANIMA: {anima} | MIC: {mic_str} | VOCE: {spk_str} "
    riga_formattata = f"{Back.BLUE}{Fore.WHITE}{' '*pad_left}{info_stato_colored}{' '*pad_right}{Style.RESET_ALL}"
    
    with stdout_lock:
        _aggiorna_dashboard_os(riga_formattata, 2)

    
def mostra_menu_modelli(modelli, attuale):
    """ "Stampa la selezione per i LLM" """
    print(f"\n{CIANO}╔════════════════ SETTAGGI MODELLO IA ════════════════╗{RESET}")
    for i, m in enumerate(modelli, 1):
        pref = f"{VERDE} >> " if m == attuale else "    "
        print(f"{pref}{i}. {m}{RESET}")
    print(f"{CIANO}╚═════════════════════════════════════════════════════╝{RESET}")
    print(f"{GIALLO}Digita il numero o premi ESC per annullare.{RESET}")

def mostra_menu_personalita(file_lista, attuale):
    """ "Stampa la selezione per i file TXT della personalità" """
    print(f"\n{MAGENTA}╔════════════════ SELEZIONE PERSONALITÀ ═══════════════╗{RESET}")
    for i, f in enumerate(file_lista, 1):
        pref = f"{VERDE} >> " if f == attuale else "    "
        print(f"{pref}{i}. {f.replace('.txt', '')}{RESET}")
    print(f"{MAGENTA}╚══════════════════════════════════════════════════════╝{RESET}")
    print(f"{GIALLO}Seleziona un'anima o premi ESC per uscire.{RESET}")

def mostra_help():
    """ "Stampa a video la vera guida dinamica generata dallo scanner plugin" """
    from core.system.plugin_loader import genera_guida_dinamica
    
    # Puliamo lo schermo per dare spazio alla guida estesa
    setup_console()
    
    # Header centrato
    intestazione = f"{CIANO}╔════════════════ {translator.t('help_title')} ════════════════╗{RESET}"
    print(f"\n{intestazione.center(90)}")
    print(f"{BIANCO}{translator.t('help_scanning')}{RESET}".center(90))
    print()
    
    try:
        guida = genera_guida_dinamica()
        if not guida:
            print(f"{ROSSO}{translator.t('help_no_modules')}{RESET}".center(90))
        else:
            for item in guida:
                tag = item['tag']
                stato = item['stato']
                desc = item['descrizione']
                comandi = item.get('comandi', {})
                esempio = item.get('esempio', '')
                
                # Variazioni cromatiche per i disattivati
                if stato == "ATTIVO":
                    col_stato = VERDE
                    bordo = CIANO
                else:
                    col_stato = ROSSO
                    bordo = Fore.LIGHTBLACK_EX
                    
                print(f"{bordo}├─ {col_stato}[{tag.upper()}] {RESET}- {translator.t('system_status', status=col_stato+stato+RESET)}")
                print(f"{bordo}│{RESET}  {BIANCO}{translator.t('help_role')}{RESET} {desc}")
                
                if comandi:
                    print(f"{bordo}│{RESET}  {GIALLO}{translator.t('help_commands')}{RESET}")
                    for cmd, spiegazione in comandi.items():
                        print(f"{bordo}│{RESET}    • {cmd} -> {spiegazione}")
                        
                if esempio:
                    print(f"{bordo}│{RESET}  {MAGENTA}{translator.t('help_example')}{RESET} {esempio}")
                    
                print(f"{bordo}│{RESET}")
                
    except Exception as e:
        print(f"{ROSSO}Errore fatale nella generazione guida dinamica: {e}{RESET}")
        
    chiusura = f"{CIANO}╚════════════════════════════════════════════════════════════╝{RESET}"
    print(f"{chiusura.center(90)}")
    print(f"\n{GIALLO}{translator.t('help_footer')}{RESET}".center(90))
    
    # Svuoto vecchie digitazioni prima di bloccare
    while msvcrt.kbhit(): msvcrt.getch()
    msvcrt.getch()
    # Pulisco uscendo e lascio il compito ad interfaccia.mostra_ui_completa
    setup_console()

def scrivi_zentra(testo):
    """ Stampa la risposta di Zentra evidenziandola in GIALLO. """
    print(f"{VERDE}Zentra:{GIALLO} {testo}{RESET}")
    
def leggi_tastiera(prefisso, input_attuale):
    if msvcrt.kbhit():
        ch_raw = msvcrt.getch()
        # Tasti funzione F1-F6
        if ch_raw in [b'\x00', b'\xe0']:
            tasto_speciale = msvcrt.getch()
            if tasto_speciale == b';': return "F1", input_attuale
            if tasto_speciale == b'<': return "F2", input_attuale
            if tasto_speciale == b'=': return "F3", input_attuale
            if tasto_speciale == b'>': return "F4", input_attuale
            if tasto_speciale == b'?': return "F5", input_attuale
            if tasto_speciale == b'@': return "F6", input_attuale
            if tasto_speciale == b'A': return "F7", input_attuale
            # Opzionale: aggiungi anche F8-F12 se vuoi
            # if tasto_speciale == b'B': return "F8", input_attuale
            # if tasto_speciale == b'C': return "F9", input_attuale
            # if tasto_speciale == b'D': return "F10", input_attuale
            # if tasto_speciale == b'E': return "F11", input_attuale
            # if tasto_speciale == b'F': return "F12", input_attuale
            return None, input_attuale

        if ch_raw == b'\x1b':  # ESC
            if input_attuale:
                return "CLEAR", ""       # cancella tutto
            else:
                return "ESC", input_attuale   # altrimenti uscita

        try: ch = ch_raw.decode('utf-8')
        except: return None, input_attuale

        if ch == '\r': return "ENTER", input_attuale
        elif ch == '\b':
            if len(input_attuale) > 0:
                input_attuale = input_attuale[:-1]
                sys.stdout.write('\b \b')
                sys.stdout.flush()
            return "CHAR", input_attuale
        else:
            input_attuale += ch
            sys.stdout.write(ch)
            sys.stdout.flush()
            return "CHAR", input_attuale

    return None, input_attuale

# --- LOGICA ANIMAZIONE PUNTINI ---

def _ciclo_puntini():
    """Mostra solo i puntini animati senza testo."""
    global animazione_attiva
    fasi = [".  ", ".. ", "...", ".. "] 
    idx = 0
    sys.stdout.write(GIALLO) 
    while animazione_attiva:
        sys.stdout.write(f"\r{fasi[idx % len(fasi)]}")
        sys.stdout.flush()
        idx += 1
        time.sleep(0.3)
    
    sys.stdout.write(f"\r   \r{RESET}")
    sys.stdout.flush()

def avvia_pensiero():
    """Lancia l'animazione in un thread separato."""
    global animazione_attiva
    if not animazione_attiva:
        animazione_attiva = True
        t = threading.Thread(target=_ciclo_puntini, daemon=True)
        t.start()

def ferma_pensiero():
    """Ferma l'animazione dei puntini."""
    global animazione_attiva
    animazione_attiva = False
    time.sleep(0.1)
    
def elenca_personalita():
    """Scansiona la cartella personalita per trovare i file .txt reali."""
    cartella = "personalita"
    if not os.path.exists(cartella): os.makedirs(cartella)
    return [os.path.basename(f) for f in glob.glob(os.path.join(cartella, "*.txt"))]

def mostra_menu_anime(anime_disponibili):
    """Mostra un menu a video per la selezione della personalità."""
    print(f"\n{CIANO}=== SELEZIONE ANIMA SISTEMA ==={RESET}")
    for i, nome in enumerate(anime_disponibili, 1):
        print(f"{GIALLO}{i}{RESET} - {nome}")
    print(f"{CIANO}================================{RESET}")
    sys.stdout.write(f"{VERDE}Scegli ID (o premi altro per annullare): {RESET}")
    sys.stdout.flush()