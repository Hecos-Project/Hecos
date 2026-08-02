"""
hecos/core/daemon/watchdog.py
─────────────────────────────────────────────────────────────────────────────
Core watchdog loop. Monitors the Hecos process, counts crash events, and
decides when to restart or give up. All crash-detection policy lives here.
─────────────────────────────────────────────────────────────────────────────
"""

import sys
import time

from .launcher import spawn_hecos, terminate_process

# Watchdog policy constants
MAX_FAST_RESTARTS   = 5   # max crashes allowed within FAST_WINDOW seconds
FAST_WINDOW_SECONDS = 30  # time window for counting "fast" crashes
RESTART_DELAY       = 3   # seconds to wait before restarting after a crash

try:
    from hecos.core.logging import logger
except ImportError:
    class _L:
        def info(self, m):    print(m)
        def warning(self, m): print(m)
        def error(self, m):   print(m)
    logger = _L()


def run_watchdog() -> None:
    """
    Main watchdog loop.
    Starts Hecos, waits for it to exit, and decides whether to restart or quit.
    """
    restart_count     = 0
    last_restart_time = time.time()
    process           = None

    logger.info("[DAEMON] Watchdog loop started.")

    while True:
        logger.info(f"[DAEMON] Starting Hecos process (Attempt #{restart_count + 1})...")

        try:
            process = spawn_hecos()
            process.wait()                  # blocks here — 0% CPU while Hecos runs
            exit_code = process.returncode

            if exit_code == 0:
                logger.info("[DAEMON] Hecos closed voluntarily (Exit 0). Shutting down supervisor.")
                sys.exit(0)

            # ── Crash detected ────────────────────────────────────────────────
            logger.warning(f"[DAEMON] ⚠️ WARNING: Hecos crashed with exit code {exit_code}.")

            now = time.time()
            if now - last_restart_time < FAST_WINDOW_SECONDS:
                restart_count += 1
            else:
                restart_count = 1           # reset counter if crash was long after the last one

            last_restart_time = now

            if restart_count > MAX_FAST_RESTARTS:
                logger.error(
                    f"[DAEMON] 🚨 {restart_count} crashes in {FAST_WINDOW_SECONDS}s. "
                    "System is unstable. Forced shutdown."
                )
                sys.exit(1)

            logger.info(f"[DAEMON] Automatic restart in {RESTART_DELAY} seconds...")
            time.sleep(RESTART_DELAY)

        except KeyboardInterrupt:
            logger.info("[DAEMON] Supervisor interrupted manually (Ctrl+C). Exiting.")
            terminate_process(process)
            sys.exit(0)

        except Exception as e:
            logger.error(f"[DAEMON] Critical error in watchdog loop: {e}")
            sys.exit(1)
