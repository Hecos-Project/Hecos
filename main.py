#!/usr/bin/env python
"""
Punto di ingresso principale per Zentra Core.
Avvia l'applicazione e gestisce le eccezioni non catturate.
"""

import sys
from dotenv import load_dotenv

# Carica le variabili d'ambiente dal file .env (se esiste) il prima possibile
load_dotenv()

# Force UTF-8 output encoding on Windows (prevents UnicodeEncodeError with box-drawing characters)
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

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
        import traceback
        logger.errore(f"[CRITICAL FAILURE]: {e}\n{traceback.format_exc()}")
        sys.exit(1)