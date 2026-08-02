"""
hecos/core/daemon/__init__.py
─────────────────────────────────────────────────────────────────────────────
Public API of the Daemon package.
Import this module to start the Supervisor programmatically.
─────────────────────────────────────────────────────────────────────────────
"""

def main() -> None:
    """Entry point for the Hecos Supervisor. Prints the banner and starts the watchdog."""
    print("==================================================")
    print(" 🛡️  HECOS SUPERVISOR (DAEMON MODE) INITIALIZED")
    print("==================================================")

    try:
        from hecos.core.logging import logger
        logger.info("[DAEMON] Supervisor (Daemon Mode) initialized. Watching for crashes.")
    except ImportError:
        pass

    from .watchdog import run_watchdog
    run_watchdog()
