#!/usr/bin/env python
"""
Punto di ingresso principale per Zentra Core.
Avvia l'applicazione e gestisce le eccezioni non catturate.
"""

import sys
from app import ZentraApplication
from core.logging import logger

def main():
    """Avvia l'applicazione Zentra."""
    app = ZentraApplication()
    try:
        app.run()
    finally:
        # Garantisce la chiusura delle finestre di log esterne in ogni caso
        logger.chiudi_tutte_le_console()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("[MAIN] Manual stop.")
    except Exception as e:
        logger.errore(f"[CRITICAL FAILURE]: {e}")
        sys.exit(1)