"""
MODULO: Motore Grafico Zentra - ui/graphics.py
DESCRIZIONE: Gestisce la generazione di elementi visuali dinamici, 
barre di progresso, slider e indicatori di stato reattivi.
"""

from colorama import Fore, Style

# Palette Colori Centralizzata
COLORI = {
    "VERDE": Fore.GREEN,
    "GIALLO": Fore.YELLOW,
    "ROSSO": Fore.RED,
    "CIANO": Fore.CYAN,
    "BIANCO": Fore.WHITE,
    "NERO": Fore.BLACK,
    "RESET": Style.RESET_ALL,
    "BRIGHT": Style.BRIGHT
}

def crea_barra(percentuale, larghezza=20, stile="cyber"):
    """
    Genera una barra di progresso testuale.
    Stili: 'cyber' (█░), 'minimal' ([#-]) o 'dot' (●○).
    """
    percentuale = max(0, min(100, percentuale))
    pieni = int((percentuale / 100) * larghezza)
    vuoti = larghezza - pieni
    
    # Selezione caratteri in base allo stile
    char_pieno, char_vuoto = "█", "░"
    if stile == "minimal": char_pieno, char_vuoto = "#", "-"
    if stile == "dot": char_pieno, char_vuoto = "●", "○"

    # Colore dinamico in base alla soglia
    colore = COLORI["VERDE"]
    if percentuale > 70: colore = COLORI["GIALLO"]
    if percentuale > 90: colore = COLORI["ROSSO"]

    barra = f"{colore}{char_pieno * pieni}{COLORI['NERO']}{char_vuoto * vuoti}{COLORI['RESET']}"
    
    # Arrotonda la percentuale a 1 decimale per la visualizzazione
    percentuale_arrotondata = round(percentuale, 1)
    
    return f"{barra} {COLORI['BRIGHT']}{percentuale_arrotondata:>3}%{COLORI['RESET']}"

def indicatore_reattivita(stato_online):
    """Restituisce un widget testuale per lo stato di Ollama/Modello."""
    if stato_online:
        return f"{COLORI['VERDE']}● ONLINE{COLORI['RESET']}"
    else:
        return f"{COLORI['ROSSO']}○ OFFLINE{COLORI['RESET']}"

def genera_slider(valore, range_max=100, etichetta="VOL"):
    """Crea uno slider orizzontale per parametri regolabili."""
    pos = int((valore / range_max) * 10)
    slider = ["-"] * 11
    slider[pos] = f"{COLORI['CIANO']}⧯{COLORI['RESET']}"
    return f"{etichetta}: <{''.join(slider)}>"