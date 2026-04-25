#!/usr/bin/env python
"""
Main entry point for Zentra Core.
Starts the application and handles uncaught exceptions.
"""

import sys
import os
import atexit
from dotenv import load_dotenv

# Bootstrap path: ensure project root is in sys.path
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# Load environment variables from .env file as soon as possible
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

from zentra.app.application import ZentraApplication
from zentra.core.logging import logger
from zentra.core.system import instance_lock

# Register the guaranteed cleanup hook
atexit.register(logger.close_all_consoles)

def main():
    """Starts the Zentra application."""
    app = ZentraApplication()
    try:
        app.run()
    finally:
        # Ensures all external log consoles are closed in any case
        logger.close_all_consoles()

if __name__ == "__main__":
    if not os.environ.get("ZENTRA_MONITORED_PROCESS"):
        if not instance_lock.acquire_lock("zentra_console"):
            print("\n[ERROR] Another instance of Zentra Console is already running.")
            sys.exit(1)
        
    try:
        main()


    except KeyboardInterrupt:
        logger.info("[MAIN] Manual stop.")
    except Exception as e:
        import traceback
        logger.error(f"[CRITICAL FAILURE]: {e}\n{traceback.format_exc()}")
        sys.exit(1)