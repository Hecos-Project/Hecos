"""
MODULO: Interface & UI - Hecos v0.18.2
DESCRIZIONE: Gestisce la UI del terminale, le dashboard hardware e i tasti funzione.

File orchestratore per retrocompatibilità. 
Implementazioni spostate in:
- terminal_renderer.py
- terminal_input.py
- terminal_menus.py
"""
import sys
import os

from colorama import init

# "Inizializzazione Colorama per colori ANSI e sfondi su Windows"
init(convert=True, autoreset=True)

# Facade for terminal_renderer.py
from hecos.ui.terminal_renderer import (
    translate_status,
    get_status_color,
    get_header_row,
    get_system_menu_row,
    get_status_bar,
    get_ptt_hint_row,
    get_hardware_row,
    show_web_access_info
)

# Facade for terminal_input.py
from hecos.ui.terminal_input import (
    set_active_prompt,
    print_scrolling,
    write_hecos,
    read_keyboard_input,
    push_cli_history
)

# Facade for terminal_menus.py
from hecos.ui.terminal_menus import (
    start_thinking,
    stop_thinking,
    list_personalities,
    show_soul_menu,
    show_personality_menu,
    show_models_menu,
    show_help,
    _dots_cycle
)


def setup_console():
    """Cleans screen and forces UTF-8. No scrolling region — we use readline-style redraw."""
    if sys.platform == 'win32':
        os.system('chcp 65001 > nul')
    
    from hecos.ui.ui_updater import update_cached_L
    update_cached_L()
    
    # Clear screen fully and reset any previous scrolling region
    # \033[H homing prevents the header from being drawn twice
    sys.stdout.write("\033[r\033[2J\033[H")
    sys.stdout.flush()


def move_to_body():
    """Moves the cursor to the body start (Row 6), right below the header."""
    sys.stdout.write("\033[6;1H")
    sys.stdout.flush()


def move_to_prompt():
    """No-op: prompt now appears naturally — no forced jump to H."""
    pass


def show_complete_ui(config, voice_status, listening_status, system_status="READY", ptt_status=False):
    """ Draws the complete interface: Blue Bar (Status), Hardware Bar and footer. """
    setup_console()
    
    from hecos.ui.ui_updater import get_cached_L
    L = get_cached_L()
    
    # Render all 5 segments using helpers
    sys.stdout.write(get_header_row(L) + "\n")
    sys.stdout.write(get_system_menu_row(L) + "\n")
    sys.stdout.write(get_status_bar(config, voice_status, listening_status, system_status, L, ptt_status) + "\n")
    sys.stdout.write(get_hardware_row(config) + "\n")
    sys.stdout.write(get_ptt_hint_row(L, system_status, ptt_status) + "\n")
    
    sys.stdout.write("\n")
    sys.stdout.flush()


def update_status_bar_in_place(config, voice_status, listening_status, system_status="READY", ptt_status=False):
    """Updates the status bar (Row 3) in-place without title-bar bloat."""
    from hecos.ui.ui_updater import _update_dashboard_os, stdout_lock, _update_title_bar
    from colorama import Back, Fore, Style
    from hecos.app.model_manager import ModelManager
    import re
    from hecos.core.i18n import translator
    import shutil
    
    # 1. Update Title Bar (Keep it clean: only app name)
    _update_title_bar("")
    
    # 2. Rebuild the Status Bar row
    try:
        backend_type, model = ModelManager.get_effective_model_info(config)
    except Exception:
        backend_type, model = "N/D", "N/D"
        
    ai_conf = config.get('ai') or {}
    soul = ai_conf.get('active_personality', 'N/D').replace('.yaml', '')
    
    mic_str = "ON" if listening_status else f"{Fore.RED}OFF{Fore.WHITE}"
    spk_str = "ON" if voice_status else f"{Fore.RED}OFF{Fore.WHITE}"
    ptt_str = "ON" if ptt_status else f"{Fore.RED}OFF{Fore.WHITE}"
    
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