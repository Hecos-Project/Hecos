#!/usr/bin/env python
# Wrapper root per Zentra Monitor
import sys
import os
import time
import argparse
import subprocess

# --- CRITICAL SYS.PATH FIX (Parent) ---
root_path = os.path.abspath(os.path.dirname(__file__))
zentra_path = os.path.join(root_path, "zentra")

sys.path.insert(0, root_path)
sys.path.insert(0, zentra_path)
# -----------------------------

if __name__ == "__main__":
    try:
        from zentra.monitor import start_and_monitor, DEFAULT_MAIN_SCRIPT
        from zentra.core.system import instance_lock
    except ImportError as e:
        print(f"[MONITOR PROXY] Errore critico nel caricamento: {e}")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Zentra Watchdog Monitor (Proxy)")
    parser.add_argument("--script", default=DEFAULT_MAIN_SCRIPT, help="Script or module to monitor")
    args = parser.parse_args()

    target_script = args.script
    legacy_modules = ["plugins", "core", "app", "zentra_bridge"]
    first_part = target_script.split('.')[0]
    if first_part in legacy_modules and not target_script.startswith("zentra."):
        target_script = f"zentra.{target_script}"
        print(f"[MONITOR PROXY] Mapping: {args.script} -> {target_script}")

    # --- INJECT PYTHONPATH FOR SUBPROCESSES ---
    # Questo garantisce che il processo figlio (Zentra) veda sia la root che la cartella zentra/
    env = os.environ.copy()
    current_pp = env.get("PYTHONPATH", "")
    new_paths = [root_path, zentra_path]
    env["PYTHONPATH"] = os.pathsep.join(new_paths + ([current_pp] if current_pp else []))
    # ------------------------------------------

    print(f"\n{'-'*55}")
    print(f" [MONITOR] Zentra Core Watchdog Proxy Active v0.15")
    print(f" Target: {target_script}")
    print(f" PYTHONPATH: {env['PYTHONPATH']}")
    print(f"{'-'*55}\n")
    
    lock_name = "zentra_console" if "main.py" in target_script else "zentra_web"
    
    if not instance_lock.acquire_lock(lock_name):
        print(f"\n[MONITOR] ERROR: Instance {lock_name} active.")
        sys.exit(1)
    
    # Nota: start_and_monitor in zentra/monitor.py usa subprocess.Popen.
    # Dobbiamo assicurarci che usi il NOSTRO ambiente.
    # Purtroppo start_and_monitor non accetta 'env' come parametro.
    # Ma se impostiamo os.environ prima della chiamata, Popen lo userà per default.
    os.environ["PYTHONPATH"] = env["PYTHONPATH"]
    
    try:
        while True:
            try:
                should_restart = start_and_monitor(target_script)
                if not should_restart: break
                time.sleep(1)
            except KeyboardInterrupt: break
            except Exception as e:
                print(f"[MONITOR] Error: {e}")
                time.sleep(5)
    finally:
        instance_lock.release_lock(lock_name)