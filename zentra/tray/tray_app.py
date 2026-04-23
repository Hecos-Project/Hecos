"""
MODULE: zentra/tray/tray_app.py
PURPOSE: Zentra Core System Tray icon — a lightweight control panel for the background service.
REQUIREMENTS: pystray, pillow (pip install pystray pillow)

USAGE:
  Run standalone: python -m zentra.tray.tray_app
  The tray icon is launched automatically by the installer at user login.

DESC:
  Displays the Zentra logo in the system notification area. Right-clicking
  opens a context menu. The icon glows green (online) or red (offline)
  depending on whether the Zentra backend is reachable on port 7070.
"""

import sys
import os
import threading
import time
import webbrowser

try:
    import pystray
    from PIL import Image, ImageDraw
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False
    # Define dummy names to avoid NameError in type hints
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


def _get_scheme() -> str:
    """Reads system.yaml to detect if HTTPS is enabled."""
    try:
        with open(SYSTEM_YAML, "r", encoding="utf-8") as f:
            content = f.read()
        # Simple line-by-line search without importing yaml (lightweight)
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
    """Returns the LAN IP of this machine (for remote access)."""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.254.254.254", 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "N/A"


def _load_icon(online: bool) -> Image.Image:
    """Loads the Zentra logo, or generates a fallback colored circle."""
    try:
        if os.path.exists(LOGO_PATH):
            img = Image.open(LOGO_PATH).convert("RGBA").resize((64, 64))
            # Tint with a color overlay to show status
            overlay = Image.new("RGBA", img.size, (0, 200, 80, 80) if online else (200, 40, 40, 80))
            return Image.alpha_composite(img, overlay)
    except Exception:
        pass

    # Fallback: generate a simple colored circle icon
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    color = (0, 220, 100, 240) if online else (200, 40, 40, 240)
    draw.ellipse([4, 4, size - 4, size - 4], fill=color)
    return img


def _build_menu(icon_ref: list):
    """Builds (or rebuilds) the System Tray menu."""
    online = _is_zentra_online()
    status_label = "🟢 Online" if online else "🔴 Offline"
    version = _get_version()
    scheme = _get_scheme()
    base_url = f"{scheme}://localhost:{ZENTRA_PORT}"
    chat_url = f"{base_url}/chat"
    config_url = f"{base_url}/zentra/config/ui"
    lan_ip = _get_lan_ip()

    def open_chat(icon, item):
        webbrowser.open(chat_url)

    def open_console(icon, item):
        import subprocess
        try:
            if sys.platform == "win32":
                # Use start command to open in a new actual console window
                script = os.path.join(_ROOT, "ZENTRA_CONSOLE_RUN_WIN.bat")
                subprocess.Popen(["start", "cmd", "/c", script], shell=True)
            else:
                script = os.path.join(_ROOT, "ZENTRA_CONSOLE_RUN.sh")
                # Try common terminals for Linux
                subprocess.Popen(["x-terminal-emulator", "-e", script])
        except Exception as e:
            print(f"[TRAY] Failed to open console: {e}")

    def open_config(icon, item):
        webbrowser.open(config_url)

    def restart_service(icon, item):
        _control_service("restart")

    def stop_service(icon, item):
        _control_service("stop")
        icon.stop()

    def show_about(icon, item):
        icon.notify(
            f"Zentra Core — v{version}\nAgentic OS & Orchestrator\nStatus: {status_label}\nLAN: {scheme}://{lan_ip}:{ZENTRA_PORT}/chat",
            "About Zentra Core"
        )

    def quit_tray(icon, item):
        icon.stop()

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
        pystray.Menu.SEPARATOR,
        
        # --- MAINTENANCE SECTION ---
        pystray.MenuItem("🔄 Restart Service", restart_service),
        pystray.MenuItem("⏹  Stop Service", stop_service),
        pystray.Menu.SEPARATOR,
        
        pystray.MenuItem(f"🖧  LAN: {lan_ip}:{ZENTRA_PORT}", None, enabled=False),
        pystray.MenuItem(f"🔌 {scheme.upper()} | {scheme}://localhost:{ZENTRA_PORT}/chat", None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("ℹ️  About", show_about),
        pystray.MenuItem("✖  Quit Tray", quit_tray),
    )


def _control_service(action: str):
    """Sends start/stop/restart command to the OS service manager."""
    import subprocess
    platform = sys.platform
    try:
        if platform == "win32":
            subprocess.run(["sc", action, "ZentraCore"], check=True)
        else:
            subprocess.run(["systemctl", "--user", action, "zentra"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"[TRAY] Service control failed ({action}): {e}")
    except FileNotFoundError:
        print(f"[TRAY] Service manager not found for action: {action}")


def _monitor_status(icon: "pystray.Icon"):
    """Background thread: periodically updates the tray icon based on service health."""
    while True:
        try:
            online = _is_zentra_online()
            icon.icon = _load_icon(online)
            icon.menu = _build_menu([icon])
        except Exception:
            pass
        time.sleep(STATUS_POLL_INTERVAL)


def run_tray():
    if not TRAY_AVAILABLE:
        print("\n[!] ERRORE: Dipendenze mancanti per la Tray Icon.")
        print("    Esegui questo comando nel terminale:")
        print("    pip install pystray pillow")
        sys.exit(1)

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
