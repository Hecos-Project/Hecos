"""
MODULO: Interfaccia e Grafica - Aura Core v0.6
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
import plugins.dashboard.main as dashboard
from core.version import get_version_string

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
    """ Disegna l'interfaccia completa: Barra Blu (Stato) e Barra Centrale (Hardware) """
    setup_console()
    
    # MODIFICATO: Legge il modello dal backend attivo
    backend_type = config.get('backend', {}).get('tipo', 'ollama')
    modello = config.get('backend', {}).get(backend_type, {}).get('modello', 'N/D')
    
    anima = config.get('ia', {}).get('personalita_attiva', 'N/D').replace('.txt', '')
    mic = "ON" if stato_ascolto else "OFF"
    spk = "ON" if stato_voce else "OFF"
    
    L = 90  # Aumentata leggermente la larghezza per ospitare la VRAM
    
        # 1. BARRA SUPERIORE (TITOLO) - NERO VERO
    titolo = f" {get_version_string()} ".center(L)
    # Usa codice ANSI diretto per nero (30) e sfondo ciano (46)
    print(f"\033[46m\033[30m{titolo}\033[0m")
    
    # 2. BARRA DI STATO DINAMICA
    info_stato = f" STATO: {stato_sistema} | MODELLO: {modello} | ANIMA: {anima} | MIC: {mic} | VOCE: {spk} "
    print(f"{Back.BLUE}{Fore.WHITE}{info_stato.center(L)}{Style.RESET_ALL}")
    
    # 3. BARRA HARDWARE (Telemetria: CPU, RAM, VRAM + stato backend)
    try:
        stats = dashboard.get_stats()  # <--- ora usa dashboard da plugins
        
        cpu = stats['cpu']
        ram = stats['ram']
        vram_text = stats['vram']
        # Usa backend_status invece di ollama_status
        backend_status = stats['backend_status']

        from ui import grafica
        barra_cpu = grafica.crea_barra(cpu, larghezza=12)
        barra_ram = grafica.crea_barra(ram, larghezza=12)
        
        # Colore per stato backend
        if backend_status == "PRONTA":
            stato_colore = Fore.GREEN
        elif backend_status in ("OFFLINE", "ERRORE", "TIMEOUT"):
            stato_colore = Fore.RED
        else:
            stato_colore = Fore.YELLOW

        info_hw = f" CPU: {barra_cpu}  RAM: {barra_ram}  VRAM: {vram_text}  {stato_colore}BACKEND: {backend_status}{Style.RESET_ALL} "
        compensazione = 60  # Adeguato per ospitare il testo aggiuntivo
        print(f"{Fore.CYAN}{info_hw.center(L + compensazione)}{Style.RESET_ALL}")
        
    except Exception as e:
        # In caso di errore, stampa un messaggio di fallback
        print(f"{Fore.RED}{'-- ERRORE TELEMETRIA HARDWARE --'.center(L)}{Style.RESET_ALL}")

    # 4. FOOTER COMANDI RAPIDI
    print(f"{Fore.CYAN}{'━' * L}{Style.RESET_ALL}")
    comandi = " F1: Guida | F2: Modelli | F3: Anima | F4: Voce | F5: Mic | F6: Reboot | F7: Config | ESC: Esci "
    print(f"{Style.DIM}{comandi.center(L)}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'━' * L}{Style.RESET_ALL}\n")
    
    
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
    """ "Stampa a video le skills leggendole dal registro o dalla cartella" """
    print(f"\n{GIALLO}╔════════════════ SKILLS & PROTOCOLLI ════════════════╗{RESET}")
    try:
        with open("core/registry.json", "r", encoding="utf-8") as f:
            db = json.load(f)
            for tag, info in db.items():
                print(f"{VERDE}[{tag.upper()}]{RESET}: {info['descrizione']}")
    except:
        print(f"{ROSSO}Nessun file registry.json trovato. Moduli base attivi.{RESET}")
    print(f"{GIALLO}╚═════════════════════════════════════════════════════╝{RESET}")
    print(f"Premi un tasto per continuare...")
    msvcrt.getch()

def scrivi_aura(testo):
    """ Stampa la risposta di Aura evidenziandola in GIALLO. """
    print(f"{VERDE}Aura:{GIALLO} {testo}{RESET}")
    
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