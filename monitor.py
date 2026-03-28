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

# Path configuration
DEFAULT_MAIN_SCRIPT = "main.py"
CONFIG_FILE = "config.json"

def get_translator():
    language = "en"
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                language = cfg.get("language", "en")
        except: pass
    
    translations = {
        "it": {
            "critical_missing": "[MONITOR] CRITICAL: {file} not found.",
            "starting": "[MONITOR] Starting Zentra ({script})...",
            "config_changed": "[MONITOR] config.json change detected. Terminating...",
            "reset_complete": "[MONITOR] Reset complete. Restarting in 2 seconds...",
            "error": "[MONITOR] Error: {error}"
        },
        "en": {
            "critical_missing": "[MONITOR] CRITICAL: {file} not found.",
            "starting": "[MONITOR] Starting Zentra ({script})...",
            "config_changed": "[MONITOR] config.json change detected. Terminating...",
            "reset_complete": "[MONITOR] Reset complete. Restarting in 2 seconds...",
            "error": "[MONITOR] Error: {error}"
        }
    }
    return lambda key, **kwargs: translations.get(language, translations["en"]).get(key, key).format(**kwargs)

t = get_translator()

def get_file_timestamp(path):
    if os.path.exists(path):
        return os.path.getmtime(path)
    return 0

def start_and_monitor(script_to_run):
    # For module-style runs (like plugins.web_ui.server), we don't check file existence directly if it contains dots
    if "." not in script_to_run or not script_to_run.endswith(".py"):
        if not os.path.exists(script_to_run) and not script_to_run.startswith("plugins."):
            print(t("critical_missing", file=script_to_run))
            return False

    last_config_time = get_file_timestamp(CONFIG_FILE)
    print(t("starting", script=script_to_run))
    
    # Process startup: handle both direct scripts and module-style runs
    if script_to_run.startswith("plugins."):
        process = subprocess.Popen([sys.executable, "-m", script_to_run])
    else:
        process = subprocess.Popen([sys.executable, script_to_run])

    try:
        while process.poll() is None:
            time.sleep(1)
            
            # config.json check
            current_config_time = get_file_timestamp(CONFIG_FILE)
            if current_config_time > last_config_time + 1:
                # Check for flag set by app to avoid unnecessary restarts
                if os.path.exists(".config_saved_by_app"):
                    try: os.remove(".config_saved_by_app")
                    except: pass
                    last_config_time = current_config_time
                    continue
                
                print(f"\n{t('config_changed')}")
                process.terminate()
                # Wait for process to close (max 5 seconds)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill() # Force close if unresponsive
                
                print(t("reset_complete"))
                time.sleep(2) # Safety pause for GPU
                return True
                
        # Natural exit:
        if process.returncode == 42:
            return True # Restart on request code 42
        else:
            return False # Normal closure or different error, do not restart
                    
    except Exception as e:
        print(t("error", error=e))
        process.kill()
    
    return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Zentra Watchdog Monitor")
    parser.add_argument("--script", default=DEFAULT_MAIN_SCRIPT, help="Script or module to monitor (e.g. main.py or plugins.web_ui.server)")
    args = parser.parse_args()

    print(f"\n{'-'*55}")
    print(f" [MONITOR] Zentra Core Watchdog Active")
    print(f" Target: {args.script}")
    print(f"{'-'*55}\n")
    
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