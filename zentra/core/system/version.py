import os

def _get_version():
    """Legge la versione dal file centralizzato core/version."""
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # core/version si trova al livello superiore rispetto a core/system/
        version_file = os.path.join(current_dir, "..", "version")
        if os.path.exists(version_file):
            with open(version_file, "r") as f:
                return f.read().strip()
    except Exception:
        pass
    return "0.0.0"

# Versione del core (letta dal file centralizzato)
VERSION = _get_version()

# Nome del progetto
PROJECT_NAME = "Zentra Core"
PROJECT_CODENAME = "Runtime Alpha"

# Data di rilascio (aggiorna quando fai una release)
RELEASE_DATE = "2026-04-11"

# Autore e copyright
AUTHOR = "Antonio Meloni"
COPYRIGHT = f"Copyright (c) 2026 {AUTHOR}. Tutti i diritti riservati."

# Repository e link
REPOSITORY = "https://github.com/yourusername/zentra-core"
DOCUMENTATION = "https://github.com/yourusername/zentra-core/wiki"

# Descrizione breve
DESCRIPTION = "Zentra - Entità Digitale Evoluta, assistente personale con accesso root al sistema"

# Informazioni aggiuntive
BUILD_INFO = {
    "python_version": "3.10+",
    "supported_platforms": ["Windows 10", "Windows 11"],
    "backend_support": ["Ollama", "KoboldCPP"],
}

def get_version_string():
    """Restituisce una stringa formattata con le informazioni di versione."""
    return f"{PROJECT_NAME} v{VERSION} ({PROJECT_CODENAME})"

def get_full_info():
    """Restituisce un dizionario con tutte le informazioni."""
    return {
        "name": PROJECT_NAME,
        "version": VERSION,
        "codename": PROJECT_CODENAME,
        "release_date": RELEASE_DATE,
        "author": AUTHOR,
        "copyright": COPYRIGHT,
        "description": DESCRIPTION,
        "repository": REPOSITORY,
        "documentation": DOCUMENTATION,
        "build": BUILD_INFO,
    }