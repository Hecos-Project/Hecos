#!/usr/bin/env python
# Wrapper root per Zentra Monitor
import sys
import os

# Aggiunge la cartella zentra al path per permettere gli import interni
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "zentra"))

if __name__ == "__main__":
    # Importa e lancia il monitor reale che ora è nel package
    from zentra.monitor import t, start_and_monitor, DEFAULT_MAIN_SCRIPT
    import argparse
    from core.system import instance_lock

    parser = argparse.ArgumentParser(description="Zentra Watchdog Monitor (Wrapper)")
    parser.add_argument("--script", default=DEFAULT_MAIN_SCRIPT, help="Script or module to monitor")
    args = parser.parse_args()

    print(f"\n{'-'*55}")
    print(f" [MONITOR] Zentra Core Watchdog Proxy Active")
    print(f" Target: {args.script} (Package Mode)")
    print(f"{'-'*55}\n")
    
    lock_name = "zentra_console" if "main.py" in args.script else "zentra_web"
    
    if not instance_lock.acquire_lock(lock_name):
        print(f"\n[MONITOR] ERROR: Another instance of Zentra ({lock_name}) is already running.")
        sys.exit(1)
    
    try:
        while True:
            try:
                # Nota: passiamo il path relativo al package se necessario, 
                # ma start_and_monitor userà sys.executable sul path passato.
                should_restart = start_and_monitor(args.script)
                if not should_restart:
                    print(f"\n[MONITOR] Zentra Core shut down normally.")
                    break
                time.sleep(1)
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"\n[MONITOR] Error: {e}")
                import time
                time.sleep(5)
    finally:
        instance_lock.release_lock(lock_name)