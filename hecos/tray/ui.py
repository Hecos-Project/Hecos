import os
import sys
import threading
import time
import webbrowser

try:
    import pystray
    from PIL import Image, ImageDraw
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False
    class Image:
        class Image: pass
    class ImageDraw: pass

from hecos.tray.config import LOGO_PATH, HECOS_PORT, _ROOT, load_settings, save_settings
from hecos.tray.utils import (
    is_hecos_online, get_lan_ip, get_scheme, get_version,
    play_beep, launch_console, terminate_consoles, get_urls
)
from hecos.tray.orchestrator import start_hecos, stop_hecos, restart_hecos
from hecos.tray.qr_viewer import show_qr_popup

def load_icon(online: bool) -> "Image.Image":
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

def refresh_ui(icon: "pystray.Icon"):
    if not icon: return
    online = is_hecos_online()
    icon.icon = load_icon(online)
    icon.menu = build_menu([icon])

def build_menu(icon_ref: list):
    settings = load_settings()
    online = is_hecos_online()
    status_label = "🟢 Online" if online else "🔴 Offline"
    version = get_version()
    scheme = get_scheme()
    chat_url, config_url = get_urls()
    lan_ip = get_lan_ip()

    svc_check = "✅" if settings["start_hecos_on_launch"] else "⬜"
    web_check = "✅" if settings["autoopen_webui"] else "⬜"

    def open_chat(icon, item):
        webbrowser.open(chat_url)

    def open_console(icon, item):
        if sys.platform == "win32":
            script = os.path.join(_ROOT, "scripts", "windows", "run", "HECOS_CONSOLE_RUN_WIN.bat")
        else:
            script = os.path.join(_ROOT, "scripts", "linux", "run", "HECOS_CONSOLE_RUN.sh")
        launch_console(script)

    def open_config(icon, item):
        webbrowser.open(config_url)

    def restart_core(icon, item):
        def _do_restart():
            play_beep(400, 100)
            play_beep(300, 150)
            terminate_consoles()
            restart_hecos()
            time.sleep(2)
            refresh_ui(icon)
        threading.Thread(target=_do_restart, daemon=True).start()

    def stop_core(icon, item):
        def _do_stop():
            play_beep(400, 100)
            play_beep(300, 150)
            terminate_consoles()
            stop_hecos()
            time.sleep(1.5)
            refresh_ui(icon)
        threading.Thread(target=_do_stop, daemon=True).start()

    def stop_core_and_quit(icon, item):
        def _do_quit():
            play_beep(400, 100)
            play_beep(300, 150)
            stop_hecos()
            time.sleep(1)
            icon.stop()
        threading.Thread(target=_do_quit, daemon=True).start()

    def show_about(icon, item):
        def _do_about():
            try:
                import tkinter as tk
                from tkinter import messagebox
                root = tk.Tk()
                root.withdraw()
                root.lift()
                root.attributes('-topmost', True)
                msg = f"Hecos — v{version}\nHelping Companion System\nStatus: {status_label}\nLAN: {scheme}://{lan_ip}:{HECOS_PORT}/chat"
                messagebox.showinfo("About Hecos", msg, master=root)
                root.destroy()
            except Exception:
                icon.notify(
                    f"Hecos — v{version}\nHelping Companion System\nStatus: {status_label}\nLAN: {scheme}://{lan_ip}:{HECOS_PORT}/chat",
                    "About Hecos"
                )
        threading.Thread(target=_do_about, daemon=True).start()

    def quit_tray(icon, item):
        terminate_consoles()
        stop_hecos()
        icon.stop()

    def show_qr(icon, item):
        threading.Thread(target=show_qr_popup, args=(scheme, lan_ip, HECOS_PORT), daemon=True).start()

    def toggle_autostart(icon, item):
        s = load_settings()
        s["start_hecos_on_launch"] = not s["start_hecos_on_launch"]
        save_settings(s)
        if s["start_hecos_on_launch"]:
            start_hecos()
        else:
            stop_hecos()
        time.sleep(2.0)
        refresh_ui(icon)

    def toggle_autoopen(icon, item):
        s = load_settings()
        s["autoopen_webui"] = not s["autoopen_webui"]
        save_settings(s)
        icon.menu = build_menu([icon])

    return pystray.Menu(
        pystray.MenuItem(f"HECOS CORE  v{version}", None, enabled=False),
        pystray.MenuItem(status_label, None, enabled=False),
        pystray.Menu.SEPARATOR,

        pystray.MenuItem("══ TERMINAL CONSOLE ══", None, enabled=False),
        pystray.MenuItem("🖥️  Launch Console", open_console),
        pystray.Menu.SEPARATOR,

        pystray.MenuItem("══ NATIVE WEB UI ══", None, enabled=False),
        pystray.MenuItem("🌐 Open Chat", open_chat),
        pystray.MenuItem("⚙️  Open Config", open_config),
        pystray.MenuItem("📱 Connect Mobile (QR)", show_qr),
        pystray.Menu.SEPARATOR,

        pystray.MenuItem("══ STARTUP SETTINGS ══", None, enabled=False),
        pystray.MenuItem(f"{svc_check} Start Core implicitly with Tray", toggle_autostart),
        pystray.MenuItem(f"{web_check} Auto-open WebUI on Startup", toggle_autoopen),
        pystray.Menu.SEPARATOR,

        pystray.MenuItem("🔄 Restart System Core", restart_core),
        pystray.MenuItem("⏹  Stop System Core", stop_core),
        pystray.MenuItem("⏹  Stop Core + Quit Tray", stop_core_and_quit),
        pystray.Menu.SEPARATOR,

        pystray.MenuItem(f"🖧  LAN: {lan_ip}:{HECOS_PORT}", None, enabled=False),
        pystray.MenuItem(f"🔌 {scheme.upper()} | {scheme}://localhost:{HECOS_PORT}/chat", None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("ℹ️  About", show_about),
        pystray.MenuItem("✖  Quit Tray", quit_tray),
    )
