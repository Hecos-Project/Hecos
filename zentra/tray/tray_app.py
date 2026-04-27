"""
MODULE: zentra/tray/tray_app.py
PURPOSE: Zentra Core System Tray icon — lightweight control panel for the background process.

USAGE:
  Run standalone: python -m zentra.tray.tray_app
  Auto-launched at user login via Registry HKCU\\Run
"""

import os
import sys
import json
import time
import threading
import webbrowser

from zentra.tray.config import SETTINGS_FILE, _DEFAULTS, ZENTRA_PORT, _ROOT, load_settings, save_settings
from zentra.tray.utils import is_zentra_online, play_beep, get_scheme
from zentra.tray.orchestrator import start_zentra, stop_zentra, is_zentra_running
from zentra.tray.hotkeys import tray_hotkeys
from zentra.tray.ui import load_icon, build_menu, refresh_ui, TRAY_AVAILABLE

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
            online = is_zentra_running()
            
            # Audible ascending ping when coming online
            if online and not was_online:
                play_beep(400, 100)
                play_beep(600, 150)
            was_online = online

            # Auto-start service if the toggle says it should be running
            if settings["start_zentra_on_launch"] and not online and not attempted_start:
                attempted_start = True
                print("[TRAY] start_zentra_on_launch=True but offline — starting Zentra subprocess…")
                threading.Thread(target=start_zentra, daemon=True).start()

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
        print("[TRAY] Zentra Tray is already running. Exiting current instance.")
        sys.exit(0)

    # Redirect all stdout/stderr to a log file to avoid pythonw.exe silent crashing
    log_dir = os.path.join(_ROOT, "zentra", "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "zentra_tray.log")
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

    online = is_zentra_running()
    icon_image = load_icon(online)

    icon = pystray.Icon(
        name="zentra_core",
        icon=icon_image,
        title="Zentra Core — Agentic OS",
        menu=build_menu([None])
    )

    monitor_thread = threading.Thread(target=_monitor_status, args=(icon,), daemon=True)
    monitor_thread.start()

    tray_hotkeys.start()

    print("[TRAY] Zentra Core tray icon started.")
    try:
        icon.run()
    finally:
        # Guarantee that if tray drops unexpectedly, we don't leave zombie subprocesses
        stop_zentra()
        pass


if __name__ == "__main__":
    run_tray()
