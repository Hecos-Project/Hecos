"""
MODULO: Motore Grafico Zentra - ui/graphics.py
DESCRIZIONE: Gestisce la generazione di elementi visuali dinamici, 
barre di progresso, slider e indicatori di stato reattivi.
"""

from colorama import Fore, Style

# Centralized Color Palette
COLORS = {
    "GREEN": Fore.GREEN,
    "YELLOW": Fore.YELLOW,
    "RED": Fore.RED,
    "CYAN": Fore.CYAN,
    "WHITE": Fore.WHITE,
    "BLACK": Fore.BLACK,
    "RESET": Style.RESET_ALL,
    "BRIGHT": Style.BRIGHT
}

# Terminal Constants
STILE_INPUT = f"{Fore.RED}# {Style.RESET_ALL}"

def create_bar(percentage, width=20, style="cyber"):
    """
    Generates a textual progress bar.
    Styles: 'cyber' (█░), 'minimal' ([#-]) or 'dot' (●○).
    """
    percentage = max(0, min(100, percentage))
    filled = int((percentage / 100) * width)
    empty = width - filled
    
    # Character selection based on style
    char_filled, char_empty = "█", "░"
    if style == "minimal": char_filled, char_empty = "#", "-"
    if style == "dot": char_filled, char_empty = "●", "○"

    # Dynamic color based on threshold
    color = COLORS["GREEN"]
    if percentage > 70: color = COLORS["YELLOW"]
    if percentage > 90: color = COLORS["RED"]

    bar = f"{color}{char_filled * filled}{COLORS['BLACK']}{char_empty * empty}{COLORS['RESET']}"
    
    # Round percentage for display
    rounded_percentage = round(percentage, 1)
    
    return f"{bar} {COLORS['BRIGHT']}{rounded_percentage:>3}%{COLORS['RESET']}"

def responsiveness_indicator(is_online):
    """Returns a textual widget for Ollama/Model status."""
    if is_online:
        return f"{COLORS['GREEN']}● ONLINE{COLORS['RESET']}"
    else:
        return f"{COLORS['RED']}○ OFFLINE{COLORS['RESET']}"

def generate_slider(value, max_range=100, label="VOL"):
    """Creates a horizontal slider for adjustable parameters."""
    pos = int((value / max_range) * 10)
    slider = ["-"] * 11
    slider[pos] = f"{COLORS['CYAN']}⧯{COLORS['RESET']}"
    return f"{label}: <{''.join(slider)}>"