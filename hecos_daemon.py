#!/usr/bin/env python
"""
hecos_daemon.py
─────────────────────────────────────────────────────────────────────────────
Hecos Supervisor / Watchdog.
Launches the main process (main.py) and monitors it. If Hecos crashes 
(exit code != 0), the Daemon restarts it automatically.
If the user closes Hecos voluntarily (exit code == 0), the Daemon shuts down.
Resource consumption: ~10-15MB RAM, 0% CPU (waiting for OS signals).
─────────────────────────────────────────────────────────────────────────────
"""

import sys
import os
import time
import subprocess

# Add root to path so we can import hecos core components
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from hecos.core.logging import logger
except ImportError:
    # Fallback if hecos package is broken
    class _L:
        def info(self, m): print(m)
        def warning(self, m): print(m)
        def error(self, m): print(m)
    logger = _L()

def main():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    main_script = os.path.join(root_dir, "main.py")
    
    print("==================================================")
    print(" 🛡️  HECOS SUPERVISOR (DAEMON MODE) INITIALIZED")
    print("==================================================")
    logger.info("[DAEMON] Supervisor (Daemon Mode) initialized. Watching for crashes.")
    
    restart_count = 0
    max_fast_restarts = 5
    last_restart_time = time.time()
    
    while True:
        logger.info(f"[DAEMON] Starting Hecos process (Start #{restart_count + 1})...")
        
        try:
            env = os.environ.copy()
            env["HECOS_MONITORED_PROCESS"] = "1"
            
            process = subprocess.Popen(
                [sys.executable, main_script],
                cwd=root_dir,
                env=env
            )
            
            process.wait()
            exit_code = process.returncode
            
            if exit_code == 0:
                logger.info(f"[DAEMON] Hecos closed voluntarily (Exit 0). Shutting down supervisor.")
                sys.exit(0)
            else:
                logger.warning(f"[DAEMON] ⚠️ WARNING: Hecos crashed with exit code {exit_code}.")
                
                now = time.time()
                if now - last_restart_time < 30:
                    restart_count += 1
                else:
                    restart_count = 1
                    
                last_restart_time = now
                
                if restart_count > max_fast_restarts:
                    logger.error("[DAEMON] 🚨 Too many consecutive crashes. System is unstable. Forced shutdown.")
                    sys.exit(1)
                    
                logger.info(f"[DAEMON] Automatic restart in 3 seconds...")
                time.sleep(3)
                
        except KeyboardInterrupt:
            logger.info("[DAEMON] Supervisor interrupted manually (Ctrl+C). Exiting.")
            if 'process' in locals() and process.poll() is None:
                process.terminate()
            sys.exit(0)
        except Exception as e:
            logger.error(f"[DAEMON] Critical error in Supervisor: {e}")
            sys.exit(1)

if __name__ == "__main__":
    main()
