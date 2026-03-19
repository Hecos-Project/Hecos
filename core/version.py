"""
Informazioni centralizzate sulla versione di Aura Core.
Tutte le componenti del sistema devono referenziare questo file.
"""

# Versione del core
VERSION_MAJOR = 0
VERSION_MINOR = 9
VERSION_PATCH = 3
VERSION = f"{VERSION_MAJOR}.{VERSION_MINOR}.{VERSION_PATCH}"

# Nome del progetto
PROJECT_NAME = "Aura Core"
PROJECT_CODENAME = "Runtime Alpha"

# Data di rilascio (aggiorna quando fai una release)
RELEASE_DATE = "2026-03-16"

# Autore e copyright
AUTHOR = "Antonio Meloni"
COPYRIGHT = f"Copyright (c) 2026 {AUTHOR}. Tutti i diritti riservati."

# Repository e link
REPOSITORY = "https://github.com/yourusername/aura-core"
DOCUMENTATION = "https://github.com/yourusername/aura-core/wiki"

# Descrizione breve
DESCRIPTION = "Aura - Entità Digitale Evoluta, assistente personale con accesso root al sistema"

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