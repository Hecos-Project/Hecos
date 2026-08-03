"""
hecos/core/daemon/__init__.py
─────────────────────────────────────────────────────────────────────────────
Public API of the Daemon package.
Import this module to start the Supervisor programmatically.
─────────────────────────────────────────────────────────────────────────────
"""

def main() -> None:
    """Entry point for the Hecos Supervisor. Prints the banner and starts the watchdog."""
    import sys
    import os

    # Force UTF-8 on Windows to avoid cp1252 UnicodeEncodeError when stdout is redirected
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass

    # ── Instance lock: prevent duplicate daemon processes ────────────────────
    try:
        from hecos.core.system import instance_lock
        if not instance_lock.acquire_lock("hecos_daemon"):
            print("[DAEMON] Another Daemon instance is already running. Exiting.")
            sys.exit(0)
    except Exception as _le:
        print(f"[DAEMON] Could not acquire lock (non-fatal): {_le}")

    is_web = "--web" in sys.argv
    mode_str = "WebUI" if is_web else "Console"

    print("==================================================")
    print(" [DAEMON] HECOS SUPERVISOR INITIALIZED")
    print(f"     Target Mode: {mode_str}")
    print("==================================================")

    try:
        from hecos.core.logging import logger
        logger.info(f"[DAEMON] Supervisor initialized. Target: {mode_str}. Watching for crashes.")
    except ImportError:
        pass

    try:
        from .watchdog import run_watchdog
        run_watchdog(is_web=is_web)
    finally:
        # Always release the lock when the daemon exits
        try:
            from hecos.core.system import instance_lock
            instance_lock.release_lock("hecos_daemon")
        except Exception:
            pass
