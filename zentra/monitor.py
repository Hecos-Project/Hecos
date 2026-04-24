"""
MODULE: Simplified Resuscitation Monitor - Zentra Core
DESCRIPTION: Monitors config.json for restarts. Supports both main app and standalone web mode.
"""

import subprocess
import time
import os
import sys
import json
import argparse
from datetime import datetime

# Force UTF-8 output encoding on Windows (prevents UnicodeEncodeError with emojis/box-drawing)
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        pass

try:
    from zentra.core.logging.hub import get_hub
except ImportError:
    get_hub = None

# Bootstrap path: ensure project root is in sys.path
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from zentra.core.system import instance_lock

# Path configuration
DEFAULT_MAIN_SCRIPT = os.path.join("zentra", "main.py")
CONFIG_FILE = os.path.join("zentra", "config", "data", "system.yaml")

# Logging configuration
LOGS_DIR = os.path.join("zentra", "logs")
os.makedirs(LOGS_DIR, exist_ok=True)
MONITOR_LOG = os.path.join(LOGS_DIR, "zentra_monitor.log")

def monitor_log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"{ts} [MONITOR] {msg}"
    print(formatted)
    try:
        with open(MONITOR_LOG, "a", encoding="utf-8") as f:
            f.write(formatted + "\n")
        if get_hub:
            hub = get_hub()
            if hub:
                hub.broadcast("INFO", msg, "MONITOR")
    except: pass

# Replace print calls with monitor_log
def print_trace(msg): monitor_log(msg)

def get_translator():
    language = "en"
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                # Semplice parsing per trovare la riga "language: xx" in YAML senza lib esterne pesanti
                for line in f:
                    if line.startswith("language:"):
                        language = line.split(":")[1].strip().strip('"\'')
                        break
        except: pass
    
    translations = {
        "it": {
            "critical_missing": "CRITICAL: {file} not found.",
            "starting": "Starting Zentra ({script})...",
            "config_changed": "system.yaml change detected. Terminating...",
            "reset_complete": "Reset complete. Restarting in 2 seconds...",
            "error": "Error: {error}"
        },
        "en": {
            "critical_missing": "CRITICAL: {file} not found.",
            "starting": "Starting Zentra ({script})...",
            "config_changed": "system.yaml change detected. Terminating...",
            "reset_complete": "Reset complete. Restarting in 2 seconds...",
            "error": "Error: {error}"
        }
    }
    return lambda key, **kwargs: translations.get(language, translations["en"]).get(key, key).format(**kwargs)

t = get_translator()

def get_file_timestamp(path):
    if os.path.exists(path):
        return os.path.getmtime(path)
    return 0

def start_and_monitor(script_to_run):
    # For module-style runs (like zentra.modules.web_ui.server), we don't check file existence directly if it contains dots
    is_module = ("." in script_to_run and not script_to_run.endswith(".py"))
    if not is_module:
        if not os.path.exists(script_to_run):
            print(t("critical_missing", file=script_to_run))
            return False

    last_config_time = get_file_timestamp(CONFIG_FILE)
    monitor_log(t("starting", script=script_to_run))
    
    # Process startup: handle both direct scripts and module-style runs
    # Inietta la root nel PYTHONPATH del sottoprocesso per garantire la risoluzione di 'zentra'
    env = os.environ.copy()
    env["PYTHONPATH"] = _ROOT + os.pathsep + env.get("PYTHONPATH", "")

    # Monitor .py files in zentra/ folder
    zentra_folder = os.path.join(_ROOT, "zentra")
    
    def get_max_py_mtime(folder):
        max_t = 0
        for root, dirs, files in os.walk(folder):
            for f in files:
                if f.endswith(".py"):
                    t = get_file_timestamp(os.path.join(root, f))
                    if t > max_t: max_t = t
        return max_t

    last_code_time = get_max_py_mtime(zentra_folder)
    
    # Process startup
    env = os.environ.copy()
    env["PYTHONPATH"] = _ROOT + os.pathsep + env.get("PYTHONPATH", "")
    if "PYTHONIOENCODING" not in env:
        env["PYTHONIOENCODING"] = "utf-8"

    if is_module:
        process = subprocess.Popen([sys.executable, "-m", script_to_run], env=env)
    else:
        process = subprocess.Popen([sys.executable, script_to_run], env=env)

    try:
        iterations = 0
        while process.poll() is None:
            time.sleep(2)  # Increased sleep for stability
            iterations += 1
            
            # 1. system.yaml check (every 2 seconds)
            current_config_time = get_file_timestamp(CONFIG_FILE)
            if current_config_time > last_config_time + 1:
                flag_path = os.path.join(_ROOT, ".config_saved_by_app")
                if os.path.exists(flag_path):
                    try:
                        os.remove(flag_path)
                        monitor_log("Config save by app acknowledged (ignoring restart).")
                    except: pass
                    last_config_time = current_config_time
                    continue
                
                monitor_log(f"system.yaml change detected. Terminating...")
                process.terminate()
                process.wait(timeout=5)
                return True

            # 2. Code files check (.py) - Every 10 seconds (5 * 2s)
            if iterations % 5 == 0:
                current_code_time = get_max_py_mtime(zentra_folder)
                if current_code_time > last_code_time + 2:
                    monitor_log(f"Code change detected in zentra/ folder. Restarting...")
                    process.terminate()
                    process.wait(timeout=5)
                    return True
                
        # Natural exit:
        if process.returncode == 42:
            time.sleep(1) # Safety pause before new incarnation
            return True # Restart on request code 42
        else:
            monitor_log(f"Process exited with code: {process.returncode}")
            return False # Normal closure or different error, do not restart
                    
    except Exception as e:
        print(t("error", error=e))
        process.kill()
    
    return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Zentra Watchdog Monitor")
    parser.add_argument("--script", default=DEFAULT_MAIN_SCRIPT, help="Script or module to monitor (e.g. main.py or modules.web_ui.server)")
    args = parser.parse_args()

    print(f"\n{'-'*55}")
    print(f" [MONITOR] Zentra Core Watchdog Active")
    monitor_log(f"Target: {args.script}")
    print(f"{'-'*55}\n")
    
    # Determine lock name based on script
    lock_name = "zentra_console" if "main.py" in args.script else "zentra_web"
    
    if not instance_lock.acquire_lock(lock_name):
        print(f"\n[MONITOR] ERROR: Another instance of Zentra ({lock_name}) is already running.")
        print(f"[MONITOR] Please close the existing instance before starting a new one.")
        sys.exit(1)
    
    try:
        while True:
            try:
                should_restart = start_and_monitor(args.script)
                if not should_restart:
                    print(f"\n[MONITOR] Zentra Core shut down normally. Exiting watchdog.")
                    break
                
                # If we are here, we need to restart
                print(f"\n[MONITOR] Restarting Zentra Core in progress...")
                time.sleep(1) # Brief pause
            except KeyboardInterrupt:
                print(f"\n[MONITOR] Watchdog terminated by user.")
                break
            except Exception as e:
                print(f"\n[MONITOR] unexpected error in watchdog loop: {e}")
                time.sleep(5) # Long pause before retry if something crashed
    finally:
        instance_lock.release_lock(lock_name)