#!/usr/bin/env python
"""
Punto di ingresso principale per Aura Core.
Avvia l'applicazione e gestisce le eccezioni non catturate.
"""

import sys
from app import AuraApplication
from core import logger

def main():
    """Avvia l'applicazione Aura."""
    app = AuraApplication()
    app.run()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("[MAIN] Arresto manuale.")
    except Exception as e:
        logger.errore(f"[CRITICAL FAILURE]: {e}")
        sys.exit(1)