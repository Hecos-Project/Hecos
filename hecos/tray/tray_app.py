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

from hecos.tray.config import SETTINGS_FILE, _DEFAULTS, _ROOT, load_settings, save_settings
from hecos.tray.browser_manager import launch_ai_ready_browser, is_ai_ready_browser_running, set_cdp_alive, _get_cdp_port
from hecos.tray.network_utils import get_scheme
from hecos.tray.system_utils import play_beep
from hecos.tray.orchestrator import start_hecos, stop_hecos, is_hecos_running
from hecos.tray.hotkeys import tray_hotkeys
from hecos.tray.ui import load_icon, build_menu, refresh_ui, TRAY_AVAILABLE
from hecos.tray.control_center import show_control_center

try:
    import pystray
except ImportError:
    pass

_singleton_socket = None
STATUS_POLL_INTERVAL = 3

def _monitor_status(icon: "pystray.Icon"):
    attempted_start = False
    was_online = False

    while True:
        try:
            settings = load_settings()
            online = is_hecos_running()
            
            # ── Update cached CDP status so build_menu() never blocks ─────────
            cdp_port = _get_cdp_port()
            set_cdp_alive(is_ai_ready_browser_running(cdp_port))
            # ─────────────────────────────────────────────────────────────────

            # TRANSITION: Offline → Online
            if online and not was_online:
                play_beep(400, 100)
                play_beep(600, 150)
                
                # Auto-open/refresh WebUI
                if settings.get("autoopen_webui", True):
                    from hecos.tray.browser_manager import intelligent_open_webui
                    # Wait for server to be fully ready
                    time.sleep(1.0)
                    intelligent_open_webui(icon, None)
                
                # Auto-open/refresh AI Browser (Headless/Integrated)
                if settings.get("autoopen_ai_browser", False):
                    from hecos.tray.browser_manager import intelligent_open_ai_browser
                    time.sleep(1.5)
                    intelligent_open_ai_browser(icon, None)

                # Auto-launch Chrome in AI-Ready mode if setting is enabled
                if settings.get("auto_launch_chrome_for_ai", False):
                    if not is_ai_ready_browser_running(cdp_port):
                        time.sleep(0.5)
                        from hecos.tray.network_utils import get_scheme
                        startup_url = settings.get("browser_startup_url", "")
                        if startup_url:
                            real_scheme = get_scheme()
                            if startup_url.startswith("http://") and real_scheme == "https":
                                startup_url = startup_url.replace("http://", "https://", 1)
                            elif startup_url.startswith("https://") and real_scheme == "http":
                                startup_url = startup_url.replace("https://", "http://", 1)
                        launch_ai_ready_browser(cdp_port=cdp_port, startup_url=startup_url)
                    
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
        title="HECOS — Helping Companion System",
        menu=build_menu([None])
    )

    # Left-click opens the Control Center
    def _on_activate(ic):
        show_control_center(ic, None)
    icon.default_action = _on_activate

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
