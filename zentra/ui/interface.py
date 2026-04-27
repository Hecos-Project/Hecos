"""
MODULO: Interface & UI - Zentra Core v0.18.2
DESCRIZIONE: Gestisce la UI del terminale, le dashboard hardware e i tasti funzione.

"Nello specifico: Disegna la barra blu di stato (modello, voce, anima) e la barra 
centrale che si collega a modules.dashboard per i dati hardware reali. Gestisce 
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
from zentra.ui import graphics
from colorama import init, Fore, Back, Style
from zentra.core.system import module_loader, version
from zentra.core.system.version import get_version_string
from zentra.core.i18n import translator

# "Inizializzazione Colorama per colori ANSI e sfondi su Windows"
init(convert=True, autoreset=True)

# Global variable for animation control
animation_active = False

# Standard color palette
GREEN = Fore.GREEN
YELLOW = Fore.YELLOW
RED = Fore.RED
CYAN = Fore.CYAN
MAGENTA = Fore.MAGENTA
WHITE = Fore.WHITE
RESET = Style.RESET_ALL

def translate_status(s):
    """Translates known status keys using the translator."""
    if not s:
        return s
    s_lower = s.lower()
    keys = ["ready", "error", "offline", "timeout", "waiting", "loading", "online", "disabled"]
    for k in keys:
        if s_lower.startswith(k):
            remainder = s[len(k):]
            return translator.t(k) + remainder
    return s

def get_status_color(s):
    """Returns the Fore color code based on current status."""
    if not s:
        return Fore.WHITE
    s_lower = s.lower()
    
    # Status -> color mapping
    if "ready" in s_lower or "pronto" in s_lower or "online" in s_lower:
        return Fore.GREEN
    if "thinking" in s_lower or "pensando" in s_lower or "loading" in s_lower:
        return Fore.YELLOW
    if "speaking" in s_lower or "parlando" in s_lower:
        return Fore.CYAN
    if "error" in s_lower or "offline" in s_lower:
        return Fore.RED
        
    return Fore.WHITE

def setup_console():
    """Cleans screen and forces UTF-8."""
    if sys.platform == 'win32':
        os.system('chcp 65001 > nul')
    # Reset scrolling region and clear screen
    sys.stdout.write("\033[r")
    os.system('cls' if os.name == 'nt' else 'clear')

def check_ollama():
    """Checks if Ollama server is active for the status bar."""
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=0.2)
        return r.status_code == 200
    except:
        return False
def show_complete_ui(config, voice_status, listening_status, system_status="READY", ptt_status=False):
    """ Draws the complete interface: Blue Bar (Status), Hardware Bar (placeholder) and Footer.
        The hardware bar will be updated in real-time by ui_updater.
    """
    setup_console()
    
    # MODIFIED: Reads model from active backend with automatic fallback
    """
    Clears the screen and prints the header (Rows 1-4) in the console buffer.
    Indices: R1=Menu, R2=Status, R3=Hardware.
    """
    from zentra.app.model_manager import ModelManager
    from zentra.core.i18n import translator
    import shutil
    import re
    
    # 1. CLEAR SCREEN (Ensures Row 1 of Viewport is Row 1 of the header)
    os.system('cls' if os.name == 'nt' else 'clear')
    
    from zentra.ui.ui_updater import get_cached_L
    L = get_cached_L()
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    
    # --- ROW 1: TITLE BAR (CYAN) ---
    from zentra.core.system.version import get_version_string
    titolo = f" {get_version_string()} "
    print(f"\033[46m\033[30m{titolo.center(L)}\033[0m")
    
    # --- ROW 2: COMMANDS MENU ---
    comandi = (
        f" {translator.t('menu_help')} | {translator.t('menu_models')} | "
        f"{translator.t('menu_persona')} | {translator.t('menu_mic')} | "
        f"{translator.t('menu_refresh')} | {translator.t('menu_voice')} | "
        f"{translator.t('menu_config')} | PTT (F8) | {translator.t('menu_reboot')} "
    )
    if len(ansi_escape.sub('', comandi)) > L:
        comandi = " F1..F4: Menu | F5: Ref | F6: Voice | F8: PTT | F9: Reb "
    print(f"{Style.DIM}{comandi.center(L)}{Style.RESET_ALL}")
    
    # --- ROW 3: STATUS BAR (BLUE) ---
    try:
        from zentra.app.model_manager import ModelManager
        _, model_eff = ModelManager.get_effective_model_info(config)
    except Exception as e:
        logger.debug(f"UI: Error getting effective model: {e}")
        model_eff = "N/D"

    # Use .get() with robust fallbacks
    ai_conf = config.get('ai') or {}
    soul = ai_conf.get('active_personality', 'N/D')
    if soul:
        soul = str(soul).replace('.yaml', '')
    else:
        soul = "N/D"

    mic_str = "ON" if listening_status else "OFF"
    spk_str = "ON" if voice_status else "OFF"
    ptt_str = "ON" if ptt_status else "OFF"
    
    status_translated = translate_status(system_status)
    status_color = get_status_color(system_status)
    info_status = translator.t("system_status", status="{S}").replace("{S}", f"{status_color}{status_translated}{Fore.WHITE}")
    header_mod = translator.t("header_model")
    header_ani = translator.t("header_soul")
    header_mic = translator.t("header_mic")
    header_voc = translator.t("header_voice")

    info_status_colored = f" {info_status} | {header_mod}: {model_eff} | {header_ani}: {soul} | {header_mic}: {mic_str} | {header_voc}: {spk_str} | PTT: {ptt_str} "
    vis_len = len(ansi_escape.sub('', info_status_colored))
    p_left = max(0, L - vis_len) // 2
    p_right = max(0, L - vis_len) - p_left
    print(f"{Back.BLUE}{Fore.WHITE}{' '*p_left}{info_status_colored}{' '*p_right}{Style.RESET_ALL}")
    
    # --- ROW 4: HARDWARE BAR (CYAN) ---
    hw_row = get_hardware_row(config, dashboard_mod=None)
    print(hw_row)
    
    # --- ROW 5: HINT BAR (Yellow) if PTT is ON ---
    if "LISTENING" in str(system_status).upper() or "RECORDING" in str(system_status).upper():
        rec_text = " 🔴 RECORDING... "
        print(f"{Back.RED}{Fore.WHITE}{Style.BRIGHT}{rec_text.center(L)}{Style.RESET_ALL}")
    elif ptt_status:
        hint_text = f" {translator.t('ptt_hint')} "
        print(f"{Fore.YELLOW}{hint_text.center(L)}{Style.RESET_ALL}")
    else:
        # Divider line
        print(f"{Fore.CYAN}{'━' * L}{Style.RESET_ALL}")
    
    sys.stdout.write("\n")
    sys.stdout.flush()
    
def get_hardware_row(config=None, dashboard_mod=None):
    """
    Returns the formatted string for the hardware row (CPU, RAM, VRAM, backend).
    Guarantees it respects the terminal width to avoid UI corruption/wrap.
    """
    from zentra.ui.ui_updater import get_cached_L
    L = get_cached_L()
    
    if dashboard_mod is None:
        dashboard_mod = module_loader.get_plugin_module("DASHBOARD")
        
    dsb_config = config.get("plugins", {}).get("DASHBOARD", {}) if config else {}
    col_dsb = dsb_config.get("console_dashboard_enabled", True)
    col_tel = dsb_config.get("console_telemetry_enabled", True)
    
    if not col_dsb:
        return f"{Fore.CYAN}{' ' * L}{Style.RESET_ALL}"
    
    if dashboard_mod:
        try:
            stats = dashboard_mod.get_stats(config)
            cpu = stats['cpu']
            ram = stats['ram']
            vram = stats['vram']
            if len(str(vram)) > 25: vram = str(vram)[:22] + ".."
            backend_status = stats['backend_status']
            
            cpu_bar = graphics.create_bar(cpu, width=5)
            ram_bar = graphics.create_bar(ram, width=5)
            
            # Translate backend status
            if backend_status in ("READY", "CLOUD", "ONLINE"):
                display_status = translator.t("ready")
                if backend_status == "CLOUD": display_status = "CLOUD"
                status_color = Fore.GREEN
            elif backend_status in ("OFFLINE", "ERROR", "TIMEOUT"):
                key = backend_status.lower() if backend_status.lower() in ["offline", "error", "timeout"] else "disabled"
                display_status = translator.t(key)
                status_color = Fore.RED
            elif backend_status == "STARTING":
                display_status = "STARTING..."
                status_color = Fore.YELLOW
            else:
                display_status = backend_status if backend_status else "--"
                status_color = Fore.YELLOW

            if col_tel:
                info_hw = translator.t("hardware_line", 
                    cpu=cpu_bar, ram=ram_bar, gpu=stats.get('gpu_load', 'N/D'), vram=vram, 
                    backend=f"{status_color}{display_status}{Style.RESET_ALL}"
                )
            else:
                # Se la telemetria è disattivata, mostriamo solo lo stato del backend
                padded = f" BACKEND AI: {status_color}{display_status}{Style.RESET_ALL} "
                # Center ignoring ansi
                import re
                ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
                v_len = len(ansi_escape.sub('', padded))
                p_l = max(0, L - v_len) // 2
                p_r = max(0, L - v_len) - p_l
                info_hw = f"{' ' * p_l}{padded}{' ' * p_r}"
                
        except Exception as e:
            info_hw = f"{Fore.RED}-- HARDWARE ERROR: {e} --{Style.RESET_ALL}"
    else:
        # Se il plugin è disabilitato, restituiamo una riga vuota di 90 spazi
        return f"{Fore.CYAN}{' ' * L}{Style.RESET_ALL}"
    
    # Explicitly truncate to avoid wrap-induced scrolling
    # We limit the visible characters, ANSI codes are extra.
    # A simple but effective way: ensure the text doesn't exceed a safe width.
    return f"{Fore.CYAN}{info_hw[:500]}{Style.RESET_ALL}"

def update_status_bar_in_place(config, voice_status, listening_status, system_status="READY", ptt_status=False):
    """Updates the status bar (Row 3) in-place without title-bar bloat."""
    from zentra.ui.ui_updater import _update_dashboard_os, stdout_lock, _update_title_bar
    from colorama import Back, Fore, Style
    from zentra.app.model_manager import ModelManager
    import re
    
    # 1. Update Title Bar (Keep it clean: only app name)
    _update_title_bar("")
    
    # 2. Rebuild the Status Bar row
    backend_type, model = ModelManager.get_effective_model_info(config)
    ai_conf = config.get('ai') or {}
    soul = ai_conf.get('active_personality', 'N/D').replace('.yaml', '')
    
    mic_str = "ON" if listening_status else f"{Fore.RED}OFF{Fore.WHITE}"
    spk_str = "ON" if voice_status else f"{Fore.RED}OFF{Fore.WHITE}"
    ptt_str = "ON" if ptt_status else f"{Fore.RED}OFF{Fore.WHITE}"
    
    import shutil
    L = max(90, shutil.get_terminal_size((115, 30)).columns - 1)
    status_translated = translate_status(system_status)
    status_color = get_status_color(system_status)
    
    info_status = translator.t("system_status", status="{S}").replace("{S}", f"{status_color}{status_translated}{Fore.WHITE}")
    header_mod = translator.t("header_model")
    header_ani = translator.t("header_soul")
    header_mic = translator.t("header_mic")
    header_voc = translator.t("header_voice")
    
    info_status_colored = f" {info_status} | {header_mod}: {model} | {header_ani}: {soul} | {header_mic}: {mic_str} | {header_voc}: {spk_str} | PTT: {ptt_str} "
    visible_len = len(re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', info_status_colored))
    pad_left = max(0, L - visible_len) // 2
    pad_right = max(0, L - visible_len) - pad_left
    
    formatted_row = f"{Back.BLUE}{Fore.WHITE}{' '*pad_left}{info_status_colored}{' '*pad_right}{Style.RESET_ALL}"
    
    with stdout_lock:
        # Write to Row 3 of the viewport (Safe absolute update)
        _update_dashboard_os(formatted_row, 3)
        
        # Update Row 5: Hint or Divider
        if "LISTENING" in str(system_status).upper() or "RECORDING" in str(system_status).upper():
            rec_text = " 🔴 RECORDING... "
            formatted_hint = f"{Back.RED}{Fore.WHITE}{Style.BRIGHT}{rec_text.center(L)}{Style.RESET_ALL}"
            _update_dashboard_os(formatted_hint, 5)
        elif ptt_status:
            hint_text = f" {translator.t('ptt_hint')} "
            formatted_hint = f"{Fore.YELLOW}{hint_text.center(L)}{Style.RESET_ALL}"
            _update_dashboard_os(formatted_hint, 5)
        else:
            divider = f"{Fore.CYAN}{'━' * L}{Style.RESET_ALL}"
            _update_dashboard_os(divider, 5)

    
def show_models_menu(categorized_models, current):
    """Prints the selection for LLM models with categorized blue sections."""
    from zentra.app.model_manager import ModelManager
    
    t_title = translator.t('model_mgmt_title')
    L = 58
    
    print(f"\n{CYAN}╔{'═' * (L)}╗{RESET}")
    print(f"{CYAN}║{WHITE} {t_title.center(L-2)} {CYAN}║{RESET}")
    print(f"{CYAN}╠{'═' * (L)}╣{RESET}")
    
    # Try to get model sizes for Ollama
    model_sizes = {}
    try:
        import requests
        resp = requests.get("http://localhost:11434/api/tags", timeout=1)
        if resp.status_code == 200:
            for m in resp.json().get('models', []):
                name = m.get('name', '')
                size = m.get('size', 0)
                if size > 1024**3:
                    model_sizes[name] = f"{size/(1024**3):.1f}GB"
                elif size > 1024**2:
                    model_sizes[name] = f"{size/(1024**2):.0f}MB"
    except:
        pass
    
    global_idx = 1
    for category, models in categorized_models.items():
        # Blue category header bar
        cat_title = f" ── {category.upper()} ── "
        print(f"{CYAN}║{Back.BLUE}{Fore.WHITE}{cat_title.center(L)}{Style.RESET_ALL}{CYAN}║{RESET}")
        print(f"{CYAN}║{'─' * (L)}║{RESET}")
        
        for m in models:
            is_active = m == current
            pref = f"{GREEN} ► " if is_active else "   "
            size_str = ""
            if category == "Ollama (Local)" and m in model_sizes:
                size_str = f"  {YELLOW}[{model_sizes[m]}]{RESET}"
            
            model_str = f"{CYAN}║{RESET} {pref}{global_idx:2}. {m}{size_str}"
            print(model_str)
            global_idx += 1
        
        print(f"{CYAN}║{RESET}")  # Blank separator line between categories
            
    print(f"{CYAN}╚{'═' * (L)}╝{RESET}")
    print(f"{YELLOW}  {translator.t('select_model_index')}{RESET}")




def show_personality_menu(file_list, current):
    """Prints the selection for personality files (F3)."""
    head = translator.t("select_personality")
    print(f"\n{MAGENTA}{head}{RESET}")
    for i, f in enumerate(file_list, 1):
        # We expect file names here. We display without .yaml suffix for cleaner UI.
        name_display = f.replace('.yaml', '')
        pref = f"{GREEN} >> " if f == current else "    "
        print(f"{pref}{i}. {name_display}{RESET}")
    print(f"{MAGENTA}{'═' * len(head)}{RESET}")
    print(f"{YELLOW}{translator.t('help_footer')}{RESET}")

def show_help():
    """Displays the dynamic guide generated by the plugin scanner."""
    from zentra.core.system.module_loader import generate_dynamic_guide
    
    # Clear the screen to make space for the extended guide
    setup_console()
    
    L = 90
    
    lang = translator.get_translator().language
    lines = []
    
    if lang == 'it':
        # ─── HEADER ─────────────────────────────────────────────────────────────────
        lines.append(f"{CYAN}╔════════════════════════════════════════════════════════════════════════════════════════╗{RESET}")
        lines.append(f"{CYAN}║{WHITE}                      ZENTRA CORE — GUIDA UTENTE (F1)                                   {CYAN}║{RESET}")
        lines.append(f"{CYAN}╚════════════════════════════════════════════════════════════════════════════════════════╝{RESET}")
        lines.append("")
        lines.append(f"{WHITE}Benvenuto! Zentra è un sistema IA modulare. Puoi comunicare usando il linguaggio")
        lines.append(f"naturale: non devi imparare comandi o sintassi complesse.{RESET}")
        lines.append("")

        # ─── SEZIONE 1: COME USARLO ─────────────────────────────────────────────────
        lines.append(f"{YELLOW}━━━ 1. COME PARLARE CON ZENTRA ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
        lines.append("")
        lines.append(f"{WHITE}  ■ Modalità Testuale:{RESET} Scrivi qualunque cosa nel prompt in basso e premi INVIO.")
        lines.append(f"    Es: {CYAN}\"Ciao, come stai?\"{RESET} oppure {CYAN}\"Mostrami i dati della CPU\"{RESET}")
        lines.append("")
        lines.append(f"{WHITE}  ■ Modalità Vocale (PC):{RESET} Tieni premuto {GREEN}CTRL+SHIFT{RESET} per attivare il microfono.")
        lines.append(f"    Parla, poi rilascia i tasti per inviare. Zentra ti risponderà a voce.")
        lines.append("")
        lines.append(f"{WHITE}  ■ Modalità Vocale (WebUI/Mobile):{RESET} Usa il pulsante 🎙️ nella chat WebUI.")
        lines.append(f"    Es: (Tap to talk) {CYAN}\"Abbassa il volume al 20%\"{RESET}")
        lines.append("")

        # ─── SEZIONE 2: TASTI FUNZIONE ──────────────────────────────────────────────
        lines.append(f"{YELLOW}━━━ 2. TASTI FUNZIONE RAPIDI (Console locale) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
        lines.append("")
        lines.append(f"{GREEN}  F1{RESET} → Mostra questa Guida Utente")
        lines.append(f"{GREEN}  F2{RESET} → Cambia il modello AI in uso (es. GPT-4, Llama locale, Gemini)")
        lines.append(f"{GREEN}  F3{RESET} → Carica una \"Personalità\" o sistema base (es. Urania, MacGyver)")
        lines.append(f"{GREEN}  F4{RESET} → Attiva o Disattiva il microfono di sistema (Privacy mute)")
        lines.append(f"{GREEN}  F5{RESET} → Aggiorna l'interfaccia (Forza il ridisegno locale)")
        lines.append(f"{GREEN}  F6{RESET} → Attiva/Disattiva la risposta Parlata (Text-to-Speech)")
        lines.append(f"{GREEN}  F7{RESET} → Editor Backend (Modifica IP, porte API, database)")
        lines.append(f"{GREEN}  F8{RESET} → Attiva/Disattiva la modalità 'Push To Talk'")
        lines.append(f"{GREEN}  F9{RESET} → Riavvia immediatamente Zentra Core")
        lines.append("")

        # ─── SEZIONE 3: COSA PUOI CHIEDERE ───────────────────────────────────────
        lines.append(f"{YELLOW}━━━ 3. ESEMPI DI UTILIZZO E COMANDI COMUNI ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
        lines.append("")
        lines.append(f"  🗣️  {CYAN}CONVERSARE E IMPARARE{RESET}")
        lines.append(f"     \"{GREEN}Spiegami in parole semplici la fisica quantistica{RESET}\"")
        lines.append(f"     \"{GREEN}Scrivi un'email di scuse per un ritardo{RESET}\"")
        lines.append(f"     \"{GREEN}Traduci questa frase in finlandese{RESET}\"")
        lines.append("")
        lines.append(f"  🖥️  {CYAN}CONTROLLO DEL COMPUTER E FILE{RESET}")
        lines.append(f"     \"{GREEN}Elenca i file che si trovano sul mio Desktop{RESET}\"")
        lines.append(f"     \"{GREEN}Apri il Blocco Note / Apri Discord{RESET}\"")
        lines.append(f"     \"{GREEN}Mostrami graficamente come va la CPU{RESET}\"")
        lines.append("")
        lines.append(f"  🌐  {CYAN}INTERNET E INFORMAZIONI{RESET}")
        lines.append(f"     \"{GREEN}Cerca in rete le ultime notizie su SpaceX{RESET}\"")
        lines.append(f"     \"{GREEN}Che giorno è oggi? / Che ore sono?{RESET}\"")
        lines.append("")
        lines.append(f"  🎵  {CYAN}CONTROLLO MEDIA E VOLUME{RESET}")
        lines.append(f"     \"{GREEN}Abbassa il volume del computer al 30%{RESET}\"")
        lines.append(f"     \"{GREEN}Metti in pausa la musica{RESET}\"")
        lines.append("")
        lines.append(f"  📸  {CYAN}FOTOCAMERA E VISIONE{RESET}")
        lines.append(f"     \"{GREEN}Scatta una foto con la webcam e dimmi cosa vedi{RESET}\"")
        lines.append(f"     \"{GREEN}Fai una foto col telefono{RESET}\" (se connesso via WebUI su mobile)")
        lines.append("")
        lines.append(f"  🎨  {CYAN}GENERAZIONE IMMAGINI AI{RESET}")
        lines.append(f"     \"{GREEN}Genera l'immagine di un cane nello spazio, stile fotorealistico{RESET}\"")
        lines.append("")
        lines.append(f"  🐍  {CYAN}ZENTRA SANDBOX (CODICE PYTHON){RESET}")
        lines.append(f"     Zentra può scrivere e autovalutare codice per risolvere calcoli o logica.")
        lines.append(f"     \"{GREEN}Calcola matematicamente la radice di 5612 in Python{RESET}\"")
        lines.append("")

        # ─── SEZIONE 4: REGOLE E OVERRIDE ───────────────────────────────────────────
        lines.append(f"{YELLOW}━━━ 4. PERSONALIZZAZIONI AVANZATE E REGOLE COMPORTAMENTALI ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
        lines.append("")
        lines.append(f"  {WHITE}■ Istruzioni Comportamentali (Special AI Instructions):{RESET}")
        lines.append(f"    Per cambiare dinamicamente il modo in cui Zentra chatta (il tono base),")
        lines.append(f"    apri la WebUI, vai in {CYAN}Configurazione > Persona{RESET} e scrivi per esempio:")
        lines.append(f"    \"{GREEN}Da ora in poi rispondimi sempre in rima{RESET}\" oppure \"{GREEN}Usa un tono sarcastico{RESET}\".")
        lines.append("")
        lines.append(f"  {WHITE}■ Plugin Routing Overrides (v0.17.0):{RESET}")
        lines.append(f"    Puoi forzare in modo potente il modo in cui Zentra usa i suoi strumenti.")
        lines.append(f"    Apri la WebUI, vai in {CYAN}Configurazione > Routing > Custom Plugin Overrides{RESET}.")
        lines.append(f"    Aggiungi una regola associata a un Tag, es:")
        lines.append(f"    Tag: {RED}WEBCAM{RESET} -> \"{GREEN}Non usare la webcam sul PC, usa sempre target='client'{RESET}\".")
        lines.append("")

        # ─── SEZIONE 5: DOCUMENTAZIONE ONLINE ───────────────────────────────────────
        lines.append(f"{YELLOW}━━━ 5. DOCUMENTAZIONE ONLINE E WIKI ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
        lines.append("")
        lines.append(f"{WHITE}  📖 Guida Utente Unificata:{RESET}  {CYAN}http://localhost:7070/zentra/docs/user{RESET}")
        lines.append(f"{WHITE}  💻 Guida Tecnica (Admin):{RESET}   {CYAN}http://localhost:7070/zentra/docs/tech{RESET}")
        lines.append(f"{WHITE}  🌐 GitHub Wiki:{RESET}             {CYAN}https://github.com/zentra-core/zentra-core/wiki{RESET}")
        lines.append("")

        # ─── SEZIONE 6: MODULI SISTEMA ──────────────────────────────────────────────
        lines.append(f"{YELLOW}━━━ 6. STATO DIAGNOSTICO DEI MODULI (TOOL ATTIVI) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
        lines.append("")
    else:
        # ─── HEADER ─────────────────────────────────────────────────────────────────
        lines.append(f"{CYAN}╔════════════════════════════════════════════════════════════════════════════════════════╗{RESET}")
        lines.append(f"{CYAN}║{WHITE}                      ZENTRA CORE — USER GUIDE (F1)                                     {CYAN}║{RESET}")
        lines.append(f"{CYAN}╚════════════════════════════════════════════════════════════════════════════════════════╝{RESET}")
        lines.append("")
        lines.append(f"{WHITE}Welcome! Zentra is a modular AI system. You can communicate using natural language:")
        lines.append(f"you don't need to learn complex commands or syntax.{RESET}")
        lines.append("")

        # ─── SECTION 1: HOW TO USE ─────────────────────────────────────────────────
        lines.append(f"{YELLOW}━━━ 1. TALKING WITH ZENTRA ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
        lines.append("")
        lines.append(f"{WHITE}  ■ Text Mode:{RESET} Type anything in the prompt below and press ENTER.")
        lines.append(f"    Ex: {CYAN}\"Hello, how are you?\"{RESET} or {CYAN}\"Show me the CPU stats\"{RESET}")
        lines.append("")
        lines.append(f"{WHITE}  ■ Voice Mode (PC):{RESET} Hold {GREEN}CTRL+SHIFT{RESET} to activate the microphone.")
        lines.append(f"    Speak, then release the keys to send. Zentra will reply by voice.")
        lines.append("")
        lines.append(f"{WHITE}  ■ Voice Mode (WebUI/Mobile):{RESET} Use the 🎙️ button in the WebUI chat.")
        lines.append(f"    Ex: (Tap to talk) {CYAN}\"Lower volume to 20%\"{RESET}")
        lines.append("")

        # ─── SECTION 2: FUNCTION KEYS ──────────────────────────────────────────────
        lines.append(f"{YELLOW}━━━ 2. QUICK FUNCTION KEYS (Local Console) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
        lines.append("")
        lines.append(f"{GREEN}  F1{RESET} → Show this User Guide")
        lines.append(f"{GREEN}  F2{RESET} → Change the active AI model (e.g., GPT-4, Local Llama, Gemini)")
        lines.append(f"{GREEN}  F3{RESET} → Load a \"Personality\" or system core (e.g., Urania, MacGyver)")
        lines.append(f"{GREEN}  F4{RESET} → Enable or Disable the system microphone (Privacy mute)")
        lines.append(f"{GREEN}  F5{RESET} → Refresh interface (Force local redraw)")
        lines.append(f"{GREEN}  F6{RESET} → Enable/Disable spoken responses (Text-to-Speech)")
        lines.append(f"{GREEN}  F7{RESET} → Backend Editor (Modify IPs, API ports, database)")
        lines.append(f"{GREEN}  F8{RESET} → Enable/Disable 'Push To Talk' mode")
        lines.append(f"{GREEN}  F9{RESET} → Immediately Reboot Zentra Core")
        lines.append("")

        # ─── SECTION 3: WHAT CAN YOU ASK ───────────────────────────────────────
        lines.append(f"{YELLOW}━━━ 3. USAGE EXAMPLES AND COMMON COMMANDS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
        lines.append("")
        lines.append(f"  🗣️  {CYAN}CONVERSE AND LEARN{RESET}")
        lines.append(f"     \"{GREEN}Explain quantum physics in simple words{RESET}\"")
        lines.append(f"     \"{GREEN}Write an apology email for a delay{RESET}\"")
        lines.append(f"     \"{GREEN}Translate this sentence into Finnish{RESET}\"")
        lines.append("")
        lines.append(f"  🖥️  {CYAN}COMPUTER AND FILE CONTROL{RESET}")
        lines.append(f"     \"{GREEN}List the files on my Desktop{RESET}\"")
        lines.append(f"     \"{GREEN}Open Notepad / Open Discord{RESET}\"")
        lines.append(f"     \"{GREEN}Show me a graph of my CPU usage{RESET}\"")
        lines.append("")
        lines.append(f"  🌐  {CYAN}INTERNET AND INFORMATION{RESET}")
        lines.append(f"     \"{GREEN}Search the web for the latest SpaceX news{RESET}\"")
        lines.append(f"     \"{GREEN}What's today's date? / What time is it?{RESET}\"")
        lines.append("")
        lines.append(f"  🎵  {CYAN}MEDIA AND VOLUME CONTROL{RESET}")
        lines.append(f"     \"{GREEN}Lower the computer volume to 30%{RESET}\"")
        lines.append(f"     \"{GREEN}Pause the music{RESET}\"")
        lines.append("")
        lines.append(f"  📸  {CYAN}CAMERA AND VISION{RESET}")
        lines.append(f"     \"{GREEN}Take a photo with the webcam and tell me what you see{RESET}\"")
        lines.append(f"     \"{GREEN}Take a photo with my phone{RESET}\" (if connected via mobile WebUI)")
        lines.append("")
        lines.append(f"  🎨  {CYAN}AI IMAGE GENERATION{RESET}")
        lines.append(f"     \"{GREEN}Generate an image of a dog in space, photorealistic style{RESET}\"")
        # ─── SECTION 4: RULES AND OVERRIDES ───────────────────────────────────────────
        lines.append(f"{YELLOW}━━━ 4. ADVANCED CUSTOMIZATIONS AND BEHAVIORAL RULES ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
        lines.append("")
        lines.append(f"  {WHITE}■ Behavioral Instructions (Special AI Instructions):{RESET}")
        lines.append(f"    To dynamically change how Zentra chats (the base tone),")
        lines.append(f"    open the WebUI, go to {CYAN}Configuration > Persona{RESET} and write for example:")
        lines.append(f"    \"{GREEN}From now on, always answer me in rhyme{RESET}\" or \"{GREEN}Use a sarcastic tone{RESET}\".")
        lines.append("")
        lines.append(f"  {WHITE}■ Plugin Routing Overrides (v0.17.0):{RESET}")
        lines.append(f"    You can powerfully force how Zentra uses its tools.")
        lines.append(f"    Open the WebUI, go to {CYAN}Configuration > Routing > Custom Plugin Overrides{RESET}.")
        lines.append(f"    Add a rule associated with a Tag, e.g.:")
        lines.append(f"    Tag: {RED}WEBCAM{RESET} -> \"{GREEN}Don't use PC webcam, always use target='client'{RESET}\".")
        lines.append("")

        # ─── SECTION 5: ONLINE DOCUMENTATION ───────────────────────────────────────
        lines.append(f"{YELLOW}━━━ 5. ONLINE DOCUMENTATION AND WIKI ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
        lines.append("")
        lines.append(f"{WHITE}  📖 Unified User Guide:{RESET}     {CYAN}http://localhost:7070/zentra/docs/user{RESET}")
        lines.append(f"{WHITE}  💻 Technical Guide (Admin):{RESET}  {CYAN}http://localhost:7070/zentra/docs/tech{RESET}")
        lines.append(f"{WHITE}  🌐 GitHub Wiki:{RESET}             {CYAN}https://github.com/zentra-core/zentra-core/wiki{RESET}")
        lines.append("")

        # ─── SECTION 6: SYSTEM MODULES ──────────────────────────────────────────────
        lines.append(f"{YELLOW}━━━ 6. SYSTEM MODULE DIAGNOSTICS (ACTIVE TOOLS) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
        lines.append("")

    for l in lines:
        print(l)
        
    
    try:
        data = generate_dynamic_guide()
        if not data:
            print(f"{RED}{translator.t('help_no_modules')}{RESET}".center(90))
        else:
            for item in data:
                tag = item['tag']
                status_text = item['status']
                desc = item['description']
                commands = item.get('commands', {})
                example = item.get('example', '')
                
                # Color variations for disabled modules
                if status_text in ("ACTIVE", "ATTIVO", "ONLINE"):
                    status_col = GREEN
                    border = CYAN
                else:
                    status_col = RED
                    border = Fore.LIGHTBLACK_EX
                    
                print(f"{border}├─ {status_col}[{tag.upper()}] {RESET}- {translator.t('system_status', status=status_col+status_text+RESET)}")
                print(f"{border}│{RESET}  {WHITE}{translator.t('help_role')}{RESET} {desc}")
                
                if commands:
                    for cmd, explanation in commands.items():
                        print(f"{border}│{RESET}    • {cmd} -> {explanation}")
                        
                print(f"{border}│{RESET}")
                
    except Exception as e:
        print(f"{RED}Fatal error generating dynamic guide: {e}{RESET}")
        
    closure = f"{CYAN}╚════════════════════════════════════════════════════════════════════════════════════════╝{RESET}"
    print(closure)
    print(f"\n{YELLOW}{translator.t('help_footer')}{RESET}".center(L))
    
    # Flush old keystrokes before blocking
    while msvcrt.kbhit(): msvcrt.getch()
    msvcrt.getch()
    # Clean up on exit and leave the task to show_complete_ui
    setup_console()

def show_web_access_info(config):
    """Prints Web UI access links if the plugin is active."""
    web_opts = config.get("plugins", {}).get("WEB_UI", {})
    port = web_opts.get("port", 7070)
    use_https = web_opts.get("https_enabled", False)
    scheme = "https" if use_https else "http"
    
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('10.254.254.254', 1))
        lan_ip = s.getsockname()[0]
        s.close()
    except Exception:
        lan_ip = "localhost"
        
    base_url = f"{scheme}://{lan_ip}:{port}"
    
    import shutil
    L = max(90, shutil.get_terminal_size((115, 30)).columns - 1)
    
    print(f"{Fore.CYAN}┌{'─' * (L-2)}┐{Style.RESET_ALL}")
    print(f"{Fore.CYAN}│{Style.RESET_ALL} {Fore.YELLOW}{'WEB INTERFACE ACCESS'.center(L-4)}{Style.RESET_ALL} {Fore.CYAN}│{Style.RESET_ALL}")
    print(f"{Fore.CYAN}├{'─' * (L-2)}┤{Style.RESET_ALL}")
    print(f"{Fore.CYAN}│{Style.RESET_ALL}  • {Fore.WHITE}Chat:  {Style.RESET_ALL} {base_url}/chat".ljust(L-1))
    print(f"{Fore.CYAN}│{Style.RESET_ALL}  • {Fore.WHITE}Config:{Style.RESET_ALL} {base_url}/zentra/config/ui".ljust(L-1))
    print(f"{Fore.CYAN}│{Style.RESET_ALL}  • {Fore.WHITE}Drive: {Style.RESET_ALL} {base_url}/drive".ljust(L-1))
    print(f"{Fore.CYAN}└{'─' * (L-2)}┘{Style.RESET_ALL}")
    print()

def write_zentra(text):
    """Prints Zentra's response highlighting it in CYAN."""
    from zentra.core.processing import filtri
    # Ensure terminal safety
    text = filtri.clean_for_video(text)
    print(Fore.CYAN + "ZENTRA: " + Style.RESET_ALL + text)
    
def read_keyboard_input(prefix, current_input):
    if msvcrt.kbhit():
        ch_raw = msvcrt.getch()
        # Function keys F1-F6
        if ch_raw in [b'\x00', b'\xe0']:
            special_key = msvcrt.getch()
            if special_key == b';': return "F1", current_input
            if special_key == b'<': return "F2", current_input
            if special_key == b'=': return "F3", current_input
            if special_key == b'>': return "F4", current_input
            if special_key == b'?': return "F5", current_input
            if special_key == b'@': return "F6", current_input
            if special_key == b'A': return "F7", current_input
            if special_key == b'B': return "F8", current_input
            if special_key == b'C': return "F9", current_input
            return None, current_input

        if ch_raw == b'\x1b':  # ESC
            if current_input:
                return "CLEAR", ""       # clear all
            else:
                return "ESC", current_input   # otherwise exit

        try: ch = ch_raw.decode('utf-8')
        except: return None, current_input

        if ch == '\r': return "ENTER", current_input
        elif ch == '\b':
            if len(current_input) > 0:
                current_input = current_input[:-1]
                sys.stdout.write('\b \b')
                sys.stdout.flush()
            return "CHAR", current_input
        else:
            current_input += ch
            sys.stdout.write(ch)
            sys.stdout.flush()
            return "CHAR", current_input

    return None, current_input

# --- DOTS ANIMATION LOGIC ---

def _dots_cycle():
    """Shows only animated dots without text."""
    global animation_active
    phases = [".  ", ".. ", "...", ".. "] 
    idx = 0
    sys.stdout.write(YELLOW) 
    while animation_active:
        sys.stdout.write(f"\r{phases[idx % len(phases)]}")
        sys.stdout.flush()
        idx += 1
        time.sleep(0.3)

def start_thinking():
    """Launches the animation in a separate thread."""
    global animation_active
    if not animation_active:
        animation_active = True
        t = threading.Thread(target=_dots_cycle, daemon=True)
        t.start()

def stop_thinking():
    """Stops the dots animation."""
    global animation_active
    animation_active = False
    sys.stdout.write(f"\r   \r{RESET}")
    sys.stdout.flush()
    
def list_personalities():
    """Scans the personality folder to find real .yaml files."""
    # Look inside the package for v0.15.2
    folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), "personality")
    if not os.path.exists(folder): os.makedirs(folder, exist_ok=True)
    return [os.path.basename(f) for f in glob.glob(os.path.join(folder, "*.yaml"))]

def show_soul_menu(available_souls):
    """Shows a menu for personality selection."""
    print(f"\n{CYAN}=== SYSTEM SOUL SELECTION ==={RESET}")
    for i, name in enumerate(available_souls, 1):
        print(f"{YELLOW}{i}{RESET} - {name}")
    print(f"{CYAN}================================{RESET}")
    sys.stdout.write(f"{GREEN}{translator.t('select_persona_index')}{RESET}")
    sys.stdout.flush()