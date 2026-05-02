"""
MODULE: hecos/tray/tray_app.py
PURPOSE: Hecos System Tray icon — lightweight control panel for the background process.

USAGE:
  Run standalone: python -m hecos.tray.tray_app
  Auto-launched at user login via Registry HKCU\\Run
"""

import os
import sys
import json
import time
import threading
import webbrowser

from hecos.tray.config import SETTINGS_FILE, _DEFAULTS, HECOS_PORT, _ROOT, load_settings, save_settings
from hecos.tray.utils import is_hecos_online, play_beep, get_scheme
from hecos.tray.orchestrator import start_hecos, stop_hecos, is_hecos_running
from hecos.tray.hotkeys import tray_hotkeys
from hecos.tray.ui import load_icon, build_menu, refresh_ui, TRAY_AVAILABLE

try:
    import pystray
except ImportError:
    pass

STATUS_POLL_INTERVAL = 3

def _monitor_status(icon: "pystray.Icon"):
    attempted_start = False
    was_online = False

    while True:
        try:
            settings = load_settings()
            online = is_hecos_running()
            
            # Audible ascending ping when coming online
            if online and not was_online:
                play_beep(400, 100)
                play_beep(600, 150)
            was_online = online

            # Auto-start service if the toggle says it should be running
            if settings["start_hecos_on_launch"] and not online and not attempted_start:
                attempted_start = True
                print("[TRAY] start_hecos_on_launch=True but offline — starting Hecos subprocess…")
                threading.Thread(target=start_hecos, daemon=True).start()

            refresh_ui(icon)

        except Exception as e:
            pass

        time.sleep(STATUS_POLL_INTERVAL)


def run_tray():
    # --- SINGLE INSTANCE LOCK ---
    import socket
    # Using a global reference to ensure the socket stays open for the life of the process
    global _singleton_socket
    _singleton_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        # We bind to a specific high-range port to ensure only one Tray instance runs per machine
        _singleton_socket.bind(("127.0.0.1", 17099))
    except (socket.error, OverflowError):
        # Already running
        print("[TRAY] Hecos Tray is already running. Exiting current instance.")
        sys.exit(0)

    # Redirect all stdout/stderr to a log file to avoid pythonw.exe silent crashing
    log_dir = os.path.join(_ROOT, "hecos", "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "hecos_tray.log")
    try:
        sys.stdout = sys.stderr = open(log_file, "a", encoding="utf-8")
    except Exception:
        pass

    if not TRAY_AVAILABLE:
        print("\n[!] ERRORE: Dipendenze mancanti per la Tray Icon.")
        print("    Esegui questo comando nel terminale:")
        print("    pip install pystray pillow")
        sys.exit(1)

    if not os.path.exists(SETTINGS_FILE):
        save_settings(_DEFAULTS)
        print(f"[TRAY] Settings file created: {SETTINGS_FILE}")

    settings = load_settings()
    print(f"[TRAY] Settings loaded: {settings}")

    online = is_hecos_running()
    icon_image = load_icon(online)

    icon = pystray.Icon(
        name="hecos_core",
        icon=icon_image,
        title="HECOS CORE — Helping Companion System",
        menu=build_menu([None])
    )

    monitor_thread = threading.Thread(target=_monitor_status, args=(icon,), daemon=True)
    monitor_thread.start()

    tray_hotkeys.start()

    print("[TRAY] Hecos tray icon started.")
    try:
        icon.run()
    finally:
        # Guarantee that if tray drops unexpectedly, we don't leave zombie subprocesses
        stop_hecos()
        pass


if __name__ == "__main__":
    run_tray()
