"""
MODULE: zentra/tray/tray_app.py
PURPOSE: Zentra Core System Tray icon — lightweight control panel for the background service.
REQUIREMENTS: pystray, pillow (pip install pystray pillow)

USAGE:
  Run standalone: python -m zentra.tray.tray_app
  Auto-launched at user login via Registry HKCU\\Run (set by install_as_service.py).

DESC:
  Displays the Zentra logo in the system notification area. Right-clicking
  opens a context menu. The icon glows green (online) or red (offline)
  depending on whether the Zentra backend is reachable on port 7070.

  SETTINGS (saved to zentra_tray_settings.json in the project root):
    service_enabled  — if True, the service is started automatically when the tray launches
    autoopen_webui   — if True, the browser opens automatically when the service comes online
"""

import sys
import os
import json
import threading
import time
import webbrowser
from datetime import datetime

try:
    from PIL import Image, ImageDraw, ImageTk
except ImportError:
    Image = None
    ImageDraw = None
    ImageTk = None

try:
    import tkinter as tk
    from tkinter import messagebox, filedialog
except ImportError:
    tk = None

try:
    import pystray
    from PIL import Image, ImageDraw
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False
    class Image:
        class Image: pass
    class ImageDraw: pass

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# === Configuration ===
ZENTRA_PORT = 7070
STATUS_POLL_INTERVAL = 10  # seconds
LOGO_PATH = os.path.join(_ROOT, "zentra", "assets", "Zentra_Core_Logo_NBG - SQR.png")
VERSION_FILE = os.path.join(_ROOT, "zentra", "core", "version")
SYSTEM_YAML = os.path.join(_ROOT, "zentra", "config", "data", "system.yaml")
SETTINGS_FILE = os.path.join(_ROOT, "zentra_tray_settings.json")


# ─────────────────────────────────────────────────────────────
#  Settings persistence
# ─────────────────────────────────────────────────────────────

_DEFAULTS = {
    "service_enabled": True,   # start the Windows service at tray startup
    "autoopen_webui": True,    # open the browser automatically when service comes online
}


def _load_settings() -> dict:
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Fill any missing keys with defaults
        for k, v in _DEFAULTS.items():
            data.setdefault(k, v)
        return data
    except Exception:
        return dict(_DEFAULTS)


def _save_settings(settings: dict):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        print(f"[TRAY] Could not save settings: {e}")


# ─────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────

def _get_scheme() -> str:
    """Reads system.yaml to detect if HTTPS is enabled."""
    try:
        with open(SYSTEM_YAML, "r", encoding="utf-8") as f:
            content = f.read()
        in_webui = False
        for line in content.splitlines():
            stripped = line.strip()
            if "WEB_UI:" in stripped:
                in_webui = True
            if in_webui and "https_enabled:" in stripped:
                value = stripped.split(":", 1)[1].strip().lower()
                if value in ("true", "yes", "1"):
                    return "https"
                break
    except Exception:
        pass
    return "http"


def _get_urls():
    scheme = _get_scheme()
    base = f"{scheme}://localhost:{ZENTRA_PORT}"
    return f"{base}/chat", f"{base}/zentra/config/ui"


def _get_version():
    try:
        with open(VERSION_FILE, "r") as f:
            return f.read().strip()
    except Exception:
        return "0.19.0"


def _is_zentra_online():
    """Checks if the Zentra backend is responding on port 7070."""
    import socket
    try:
        with socket.create_connection(("localhost", ZENTRA_PORT), timeout=2):
            return True
    except OSError:
        return False


def _get_lan_ip() -> str:
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.254.254.254", 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "N/A"


def _control_service(action: str):
    """Sends start/stop/restart command to the OS service manager."""
    import subprocess
    try:
        if sys.platform == "win32":
            if action == "restart":
                # sc.exe has no 'restart' subcommand — stop then start
                subprocess.run(["sc", "stop", "ZentraCore"], capture_output=True)
                time.sleep(3)  # Give the service time to fully stop
                subprocess.run(["sc", "start", "ZentraCore"], check=True, capture_output=True)
            else:
                subprocess.run(["sc", action, "ZentraCore"], check=True, capture_output=True)
        else:
            subprocess.run(["systemctl", "--user", action, "zentra"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"[TRAY] Service control failed ({action}): {e}")
    except FileNotFoundError:
        print(f"[TRAY] Service manager not found for action: {action}")


def _is_service_running() -> bool:
    """Returns True if the ZentraCore Windows service is in a running state."""
    if sys.platform != "win32":
        return _is_zentra_online()
    import subprocess
    try:
        result = subprocess.run(
            ["sc", "query", "ZentraCore"],
            capture_output=True, text=True
        )
        return "RUNNING" in result.stdout
    except Exception:
        return False


def _load_icon(online: bool) -> "Image.Image":
    try:
        if os.path.exists(LOGO_PATH):
            img = Image.open(LOGO_PATH).convert("RGBA").resize((64, 64))
            overlay = Image.new("RGBA", img.size, (0, 200, 80, 80) if online else (200, 40, 40, 80))
            return Image.alpha_composite(img, overlay)
    except Exception:
        pass
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    color = (0, 220, 100, 240) if online else (200, 40, 40, 240)
    draw.ellipse([4, 4, size - 4, size - 4], fill=color)
    return img


# ─────────────────────────────────────────────────────────────
#  Menu builder
# ─────────────────────────────────────────────────────────────

def _build_menu(icon_ref: list):
    """Builds (or rebuilds) the System Tray context menu."""
    settings = _load_settings()
    online = _is_zentra_online()
    status_label = "🟢 Online" if online else "🔴 Offline"
    version = _get_version()
    scheme = _get_scheme()
    base_url = f"{scheme}://localhost:{ZENTRA_PORT}"
    chat_url = f"{base_url}/chat"
    config_url = f"{base_url}/zentra/config/ui"
    lan_ip = _get_lan_ip()

    svc_check = "✅" if settings["service_enabled"] else "⬜"
    web_check = "✅" if settings["autoopen_webui"] else "⬜"

    # ── Actions ──────────────────────────────────────────────

    def open_chat(icon, item):
        webbrowser.open(chat_url)

    def open_console(icon, item):
        import subprocess
        try:
            if sys.platform == "win32":
                script = os.path.join(_ROOT, "ZENTRA_CONSOLE_RUN_WIN.bat")
                subprocess.Popen(["start", "cmd", "/c", script], shell=True)
            else:
                script = os.path.join(_ROOT, "ZENTRA_CONSOLE_RUN.sh")
                subprocess.Popen(["x-terminal-emulator", "-e", script])
        except Exception as e:
            print(f"[TRAY] Failed to open console: {e}")

    def open_config(icon, item):
        webbrowser.open(config_url)

    def restart_service(icon, item):
        """Stop + Start the backend service. The tray stays alive."""
        def _do_restart():
            threading.Thread(target=_control_service, args=("restart",), daemon=True).start()
        threading.Thread(target=_do_restart, daemon=True).start()

    def stop_service(icon, item):
        """Stop only the backend service. The tray stays alive."""
        threading.Thread(target=_control_service, args=("stop",), daemon=True).start()

    def stop_service_and_quit(icon, item):
        """Stop the backend service AND close the tray icon."""
        threading.Thread(target=_control_service, args=("stop",), daemon=True).start()
        time.sleep(1)
        icon.stop()

    def show_about(icon, item):
        icon.notify(
            f"Zentra Core — v{version}\nAgentic OS & Orchestrator\nStatus: {status_label}\nLAN: {scheme}://{lan_ip}:{ZENTRA_PORT}/chat",
            "About Zentra Core"
        )

    def quit_tray(icon, item):
        icon.stop()

    def show_qr(icon, item):
        threading.Thread(target=_show_qr_popup, args=(_get_scheme(), _get_lan_ip(), ZENTRA_PORT), daemon=True).start()

    # ── Toggle: Service Enabled ───────────────────────────────

    def toggle_service(icon, item):
        s = _load_settings()
        s["service_enabled"] = not s["service_enabled"]
        _save_settings(s)
        if s["service_enabled"]:
            print("[TRAY] Service toggled ON — starting service…")
            threading.Thread(target=_control_service, args=("start",), daemon=True).start()
        else:
            print("[TRAY] Service toggled OFF — stopping service…")
            threading.Thread(target=_control_service, args=("stop",), daemon=True).start()
        # Rebuild menu after a short delay so sc has time to respond
        time.sleep(1.5)
        icon.menu = _build_menu([icon])

    # ── Toggle: Auto-open WebUI ───────────────────────────────

    def toggle_autoopen(icon, item):
        s = _load_settings()
        s["autoopen_webui"] = not s["autoopen_webui"]
        _save_settings(s)
        icon.menu = _build_menu([icon])

    # ── QR popup helper ───────────────────────────────────────

    return pystray.Menu(
        pystray.MenuItem(f"ZENTRA CORE  v{version}", None, enabled=False),
        pystray.MenuItem(status_label, None, enabled=False),
        pystray.Menu.SEPARATOR,

        # --- TERMINAL SECTION ---
        pystray.MenuItem("══ TERMINAL CONSOLE ══", None, enabled=False),
        pystray.MenuItem("🖥️  Launch Console", open_console),
        pystray.Menu.SEPARATOR,

        # --- WEB UI SECTION ---
        pystray.MenuItem("══ NATIVE WEB UI ══", None, enabled=False),
        pystray.MenuItem("🌐 Open Chat", open_chat),
        pystray.MenuItem("⚙️  Open Config", open_config),
        pystray.MenuItem("📱 Connect Mobile (QR)", show_qr),
        pystray.Menu.SEPARATOR,

        # --- SETTINGS / TOGGLES ---
        pystray.MenuItem("══ STARTUP SETTINGS ══", None, enabled=False),
        pystray.MenuItem(f"{svc_check} Service Active in Background", toggle_service),
        pystray.MenuItem(f"{web_check} Auto-open WebUI on Startup", toggle_autoopen),
        pystray.Menu.SEPARATOR,

        # --- MAINTENANCE SECTION ---
        pystray.MenuItem("🔄 Restart Service", restart_service),
        pystray.MenuItem("⏹  Stop Service", stop_service),
        pystray.MenuItem("⏹  Stop Service + Quit Tray", stop_service_and_quit),
        pystray.Menu.SEPARATOR,

        pystray.MenuItem(f"🖧  LAN: {lan_ip}:{ZENTRA_PORT}", None, enabled=False),
        pystray.MenuItem(f"🔌 {scheme.upper()} | {scheme}://localhost:{ZENTRA_PORT}/chat", None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("ℹ️  About", show_about),
        pystray.MenuItem("✖  Quit Tray", quit_tray),
    )


# ─────────────────────────────────────────────────────────────
#  QR popup (Tkinter)
# ─────────────────────────────────────────────────────────────

def _show_qr_popup(scheme: str, lan_ip: str, port: int):
    url = f"{scheme}://{lan_ip}:{port}/chat"
    if not tk:
        print("[TRAY] Tkinter non disponibile.")
        return
    try:
        import qrcode
    except ImportError:
        print("[TRAY] qrcode library not found. Install with: pip install qrcode[pil]")
        return

    root = tk.Tk()
    root.title("Zentra Core - Mobile Connection")
    root.geometry("350x480")
    root.resizable(False, False)
    root.attributes("-topmost", True)

    bg_color = "#0d0e14"
    fg_color = "#ffffff"
    root.configure(bg=bg_color)

    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    img_qr_pil = qr.make_image(fill_color="black", back_color="white")

    tk.Label(root, text="SCAN TO CONNECT", font=("Consolas", 12, "bold"), bg=bg_color, fg="#00e676").pack(pady=(20, 5))
    tk.Label(root, text=f"URL: {url}", font=("Consolas", 8), bg=bg_color, fg="#aaaaaa", wraplength=300).pack(pady=5)

    preview_img = img_qr_pil.resize((250, 250))
    img_tk = ImageTk.PhotoImage(preview_img)
    panel = tk.Label(root, image=img_tk, bg="white", bd=0)
    panel.image = img_tk
    panel.pack(pady=10)

    def copy_url():
        root.clipboard_clear()
        root.clipboard_append(url)
        messagebox.showinfo("Copiato", "Indirizzo copiato negli appunti!")

    def save_qr():
        fpath = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png")],
            initialfile="zentra_mobile_connect.png"
        )
        if fpath:
            img_qr_pil.save(fpath)
            messagebox.showinfo("Salvato", f"QR Code salvato in:\n{fpath}")

    btn_frame = tk.Frame(root, bg=bg_color)
    btn_frame.pack(pady=10)
    tk.Button(btn_frame, text="📋 Copy URL", command=copy_url, bg="#1e1f26", fg=fg_color, bd=0, padx=10, pady=5).pack(side="left", padx=5)
    tk.Button(btn_frame, text="💾 Save PNG", command=save_qr, bg="#1e1f26", fg=fg_color, bd=0, padx=10, pady=5).pack(side="left", padx=5)
    tk.Button(root, text="Close", command=root.destroy, bg="#333", fg=fg_color, bd=0, padx=20).pack(pady=10)
    root.mainloop()


# ─────────────────────────────────────────────────────────────
#  Background monitor
# ─────────────────────────────────────────────────────────────

def _monitor_status(icon: "pystray.Icon"):
    """
    Background thread:
      - Periodically updates tray icon color (green/red) based on service health.
      - Once the service comes online, opens the browser IF autoopen_webui is enabled.
      - If service_enabled=True and the service is stopped, tries to start it once.
    """
    has_opened_browser = False
    attempted_service_start = False

    while True:
        try:
            settings = _load_settings()
            online = _is_zentra_online()

            # Auto-start service if the toggle says it should be running
            if settings["service_enabled"] and not online and not attempted_service_start:
                attempted_service_start = True
                print("[TRAY] service_enabled=True but service offline — starting service…")
                threading.Thread(target=_control_service, args=("start",), daemon=True).start()

            icon.icon = _load_icon(online)
            icon.menu = _build_menu([icon])

            # Open browser once when the service first comes online
            if online and not has_opened_browser and settings["autoopen_webui"]:
                has_opened_browser = True
                scheme = _get_scheme()
                url = f"{scheme}://127.0.0.1:{ZENTRA_PORT}/chat"
                print(f"[TRAY] System online. Auto-opening WebUI: {url}")
                webbrowser.open(url)

        except Exception as e:
            print(f"[TRAY] Monitor error: {e}")

        time.sleep(STATUS_POLL_INTERVAL)


# ─────────────────────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────────────────────

def run_tray():
    if not TRAY_AVAILABLE:
        print("\n[!] ERRORE: Dipendenze mancanti per la Tray Icon.")
        print("    Esegui questo comando nel terminale:")
        print("    pip install pystray pillow")
        sys.exit(1)

    # On first run, create the settings file with defaults if missing
    if not os.path.exists(SETTINGS_FILE):
        _save_settings(_DEFAULTS)
        print(f"[TRAY] Settings file created: {SETTINGS_FILE}")

    settings = _load_settings()
    print(f"[TRAY] Settings loaded — service_enabled={settings['service_enabled']}, autoopen_webui={settings['autoopen_webui']}")

    online = _is_zentra_online()
    icon_image = _load_icon(online)

    icon = pystray.Icon(
        name="zentra_core",
        icon=icon_image,
        title="Zentra Core — Agentic OS",
        menu=_build_menu([None])
    )

    # Start background health monitor thread
    monitor_thread = threading.Thread(target=_monitor_status, args=(icon,), daemon=True)
    monitor_thread.start()

    print("[TRAY] Zentra Core tray icon started.")
    icon.run()


if __name__ == "__main__":
    run_tray()
