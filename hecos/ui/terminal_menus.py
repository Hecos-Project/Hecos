"""
hecos/ui/terminal_menus.py
Handles CLI interactive selection menus (F2 LLM Models, F3 Personalities/Souls).
Re-exports spinner utilities and the full-screen user guide for complete backward compatibility.
"""

import glob
import os
import sys
from typing import Dict, List
from colorama import Fore, Back, Style

from hecos.core.i18n import translator

# Backward-compatible re-exports
from hecos.ui.terminal_spinner import (
    start_thinking,
    stop_thinking,
    _dots_cycle,
    animation_active,
)
from hecos.ui.help_screen import show_help

GREEN   = Fore.GREEN
YELLOW  = Fore.YELLOW
RED     = Fore.RED
CYAN    = Fore.CYAN
MAGENTA = Fore.MAGENTA
WHITE   = Fore.WHITE
RESET   = Style.RESET_ALL


def list_personalities() -> List[str]:
    """Scans the personality folder to find real .yaml files."""
    folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), "personality")
    if not os.path.exists(folder):
        os.makedirs(folder, exist_ok=True)
    return [os.path.basename(f) for f in glob.glob(os.path.join(folder, "*.yaml"))]


def show_soul_menu(available_souls: List[str]) -> None:
    """Shows a menu for personality selection."""
    print(f"\n{CYAN}=== SYSTEM SOUL SELECTION ==={RESET}")
    for i, name in enumerate(available_souls, 1):
        print(f"{YELLOW}{i}{RESET} - {name}")
    print(f"{CYAN}================================{RESET}")
    sys.stdout.write(f"{GREEN}{translator.t('select_persona_index')}{RESET}")
    sys.stdout.flush()


def show_personality_menu(file_list: List[str], current: str) -> None:
    """Prints the selection for personality files (F3)."""
    head = translator.t("select_personality")
    print(f"\n{MAGENTA}{head}{RESET}")
    for i, f in enumerate(file_list, 1):
        name_display = f.replace('.yaml', '')
        pref = f"{GREEN} >> " if f == current else "    "
        print(f"{pref}{i}. {name_display}{RESET}")
    print(f"{MAGENTA}{'═' * len(head)}{RESET}")
    print(f"{YELLOW}{translator.t('help_footer')}{RESET}")


def show_models_menu(categorized_models: Dict[str, List[str]], current: str) -> None:
    """Prints the selection for LLM models with categorized blue sections (F2)."""
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

    t_title = translator.t('model_mgmt_title')
    L = 58
    
    print(f"\n{CYAN}╔{'═' * (L)}╗{RESET}")
    print(f"{CYAN}║{WHITE} {t_title.center(L-2)} {CYAN}║{RESET}")
    print(f"{CYAN}╠{'═' * (L)}╣{RESET}")
    
    # Query model sizes and capabilities from Ollama
    model_sizes = {}
    model_caps  = {}
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
                caps = [c for c in m.get('capabilities', []) if c != 'completion']
                if caps:
                    model_caps[name] = caps
    except Exception:
        pass

    CAP_COLORS = {
        'tools':    f"{Fore.GREEN}",
        'vision':   f"{Fore.CYAN}",
        'thinking': f"{Fore.MAGENTA}",
        'embed':    f"{Fore.YELLOW}",
    }
    CAP_ICONS = {
        'tools':    '[T]',
        'vision':   '[V]',
        'thinking': '[R]',
        'embed':    '[E]',
    }

    global_idx = 1
    for category, models in categorized_models.items():
        cat_title = f" ── {category.upper()} ── "
        print(f"{CYAN}║{Back.BLUE}{Fore.WHITE}{cat_title.center(L)}{Style.RESET_ALL}{CYAN}║{RESET}")
        print(f"{CYAN}║{'─' * (L)}║{RESET}")

        for m in models:
            is_active = m == current
            pref = f"{GREEN} ► " if is_active else "   "
            size_str = ""
            caps_str = ""
            if category == "Ollama (Local)":
                if m in model_sizes:
                    size_str = f"  {YELLOW}[{model_sizes[m]}]{RESET}"
                if m in model_caps:
                    badges = []
                    for cap in model_caps[m]:
                        color = CAP_COLORS.get(cap, Fore.WHITE)
                        icon  = CAP_ICONS.get(cap, cap)
                        badges.append(f"{color}{icon}{RESET}")
                    caps_str = " " + " ".join(badges)

            model_str = f"{CYAN}║{RESET} {pref}{global_idx:2}. {m}{size_str}{caps_str}"
            print(model_str)
            global_idx += 1

        print(f"{CYAN}║{RESET}")

    if model_caps:
        legend_parts = [f"{v}{CAP_ICONS[k]}{RESET}={k}" for k, v in CAP_COLORS.items()]
        legend = "  Legend: " + "  ".join(legend_parts)
        print(f"{CYAN}║{RESET}{legend}")
        print(f"{CYAN}║{RESET}")

    print(f"{CYAN}╚{'═' * (L)}╝{RESET}")
    print(f"{YELLOW}  {translator.t('select_model_index')}{RESET}")
