"""
hecos/tray/ui.py
Hecos System Tray — Menu Builder (v2)

Key fixes vs v1:
  • Toggle items use pystray's `checked=` callback → menu stays open after click
  • CDP status is read from a cached bool (_CDP_ALIVE in utils.py), never blocking
  • Shorter root menu via submenus → faster hover rendering on slow GPUs
  • Browser submenu lists all discovered browsers + built-in Playwright Chromium
  • Optional Technical/Debug submenu, toggled from within the menu
"""

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
    play_beep, launch_console, terminate_consoles, get_urls,
    launch_ai_ready_browser, is_ai_ready_browser_running,
    get_cdp_alive, discover_browsers, launch_browser,
)
from hecos.tray.orchestrator import start_hecos, stop_hecos, restart_hecos
from hecos.tray.qr_viewer import show_qr_popup


# ── Icon rendering ─────────────────────────────────────────────────────────────

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
    """Rebuild icon image and menu — called by the background monitor."""
    if not icon:
        return
    online = is_hecos_online()
    icon.icon = load_icon(online)
    icon.menu = build_menu([icon])


# ── Browser helpers ────────────────────────────────────────────────────────────

def open_ai_browser(icon, item):
    """Launch the Playwright AI browser (or navigate to startup URL if already running)."""
    try:
        from hecos.modules.browser import engine
        s = load_settings()
        headless    = s.get("browser_headless", False)
        startup_url = s.get("browser_startup_url", "")
        mode        = s.get("browser_engine_mode", "app_mode")
        cdp_port    = s.get("cdp_port", 9222)
        if not engine.is_running():
            engine.launch(headless=headless, mode=mode, cdp_port=cdp_port)
        if startup_url:
            if startup_url == "http://localhost:7070":
                scheme = get_scheme()
                startup_url = f"{scheme}://localhost:{HECOS_PORT}"
            elif not startup_url.startswith(("http://", "https://", "file://", "about:")):
                startup_url = "https://" + startup_url
            page = engine.get_page()
            if page:
                page.goto(startup_url, wait_until="domcontentloaded")
    except Exception as e:
        print(f"[TRAY] AI Browser launch error: {e}")


def close_ai_browser(icon, item):
    try:
        from hecos.modules.browser import engine
        engine.close()
    except Exception as e:
        print(f"[TRAY] AI Browser close error: {e}")


def _get_cdp_port() -> int:
    """Read the CDP port from system.yaml (fallback 9222)."""
    try:
        from hecos.tray.config import SYSTEM_YAML
        with open(SYSTEM_YAML, "r", encoding="utf-8") as f:
            content = f.read()
        in_browser = False
        for line in content.splitlines():
            stripped = line.strip()
            if "BROWSER:" in stripped:
                in_browser = True
            if in_browser and "cdp_port:" in stripped:
                return int(stripped.split(":", 1)[1].strip())
    except Exception:
        pass
    return 9222


# ── Menu builder ───────────────────────────────────────────────────────────────

def build_menu(icon_ref: list):
    """
    Build the full pystray menu.
    Uses cached values for network-dependent status (CDP alive) so the menu
    renders instantly without blocking on any socket call.
    """
    settings     = load_settings()
    online       = is_hecos_online()
    version      = get_version()
    scheme       = get_scheme()
    chat_url, config_url = get_urls()
    lan_ip       = get_lan_ip()
    cdp_port     = _get_cdp_port()
    # Read from cache — updated every 3 s by _monitor_status
    ai_browser_live   = get_cdp_alive()
    ai_browser_status = "🟢" if ai_browser_live else "🔴"
    status_label      = "🟢 Online" if online else "🔴 Offline"
    show_tech         = settings.get("show_technical_menu", True)

    icon = icon_ref[0]  # may be None during initial build

    # ── Shared action callbacks ───────────────────────────────────────────────

    def open_chat(icon, item):
        webbrowser.open(chat_url)

    def open_config(icon, item):
        webbrowser.open(config_url)

    def show_qr(icon, item):
        threading.Thread(target=show_qr_popup, args=(scheme, lan_ip, HECOS_PORT), daemon=True).start()

    def start_core_btn(icon, item):
        def _do():
            play_beep(400, 100)
            start_hecos()
            time.sleep(2)
            refresh_ui(icon)
        threading.Thread(target=_do, daemon=True).start()

    def restart_core(icon, item):
        def _do():
            play_beep(400, 100)
            play_beep(300, 150)
            terminate_consoles()
            restart_hecos()
            time.sleep(2)
            refresh_ui(icon)
        threading.Thread(target=_do, daemon=True).start()

    def stop_core(icon, item):
        def _do():
            play_beep(400, 100)
            play_beep(300, 150)
            terminate_consoles()
            stop_hecos()
            time.sleep(1.5)
            refresh_ui(icon)
        threading.Thread(target=_do, daemon=True).start()

    def stop_core_and_quit(icon, item):
        def _do():
            play_beep(400, 100)
            play_beep(300, 150)
            stop_hecos()
            time.sleep(1)
            icon.stop()
        threading.Thread(target=_do, daemon=True).start()

    def quit_tray(icon, item):
        terminate_consoles()
        stop_hecos()
        icon.stop()

    # ── AI Chrome callbacks ───────────────────────────────────────────────────

    def do_launch_ai_ready_browser(icon, item):
        def _do():
            cdp = _get_cdp_port()
            url = load_settings().get("browser_startup_url", "")
            if url:
                real_scheme = get_scheme()
                if url.startswith("http://") and real_scheme == "https":
                    url = url.replace("http://", "https://", 1)
                elif url.startswith("https://") and real_scheme == "http":
                    url = url.replace("https://", "http://", 1)
            launch_ai_ready_browser(cdp_port=cdp, startup_url=url)
            time.sleep(1.5)
            refresh_ui(icon)
        threading.Thread(target=_do, daemon=True).start()

    # ── Settings toggles (use checked= so menu stays open) ───────────────────

    def toggle_autostart(icon, item):
        s = load_settings()
        s["start_hecos_on_launch"] = not s["start_hecos_on_launch"]
        save_settings(s)
        icon.menu = build_menu([icon])

    def toggle_autoopen(icon, item):
        s = load_settings()
        s["autoopen_webui"] = not s["autoopen_webui"]
        save_settings(s)
        icon.menu = build_menu([icon])

    def toggle_autoopen_ai_browser(icon, item):
        s = load_settings()
        s["autoopen_ai_browser"] = not s.get("autoopen_ai_browser", False)
        save_settings(s)
        icon.menu = build_menu([icon])

    def toggle_auto_launch_chrome(icon, item):
        s = load_settings()
        s["auto_launch_chrome_for_ai"] = not s.get("auto_launch_chrome_for_ai", False)
        save_settings(s)
        icon.menu = build_menu([icon])

    def toggle_technical_menu(icon, item):
        s = load_settings()
        s["show_technical_menu"] = not s.get("show_technical_menu", True)
        save_settings(s)
        icon.menu = build_menu([icon])

    # ── Technical-menu callbacks ──────────────────────────────────────────────

    def open_console(icon, item):
        if sys.platform == "win32":
            script = os.path.join(_ROOT, "scripts", "windows", "run", "HECOS_CONSOLE_RUN_WIN.bat")
        else:
            script = os.path.join(_ROOT, "scripts", "linux", "run", "HECOS_CONSOLE_RUN.sh")
        launch_console(script)

    def copy_lan_ip(icon, item):
        def _do():
            try:
                import tkinter as tk
                root = tk.Tk(); root.withdraw()
                root.clipboard_clear()
                root.clipboard_append(f"{scheme}://{lan_ip}:{HECOS_PORT}")
                root.update(); root.destroy()
            except Exception:
                pass
        threading.Thread(target=_do, daemon=True).start()

    def copy_local_url(icon, item):
        def _do():
            try:
                import tkinter as tk
                root = tk.Tk(); root.withdraw()
                root.clipboard_clear()
                root.clipboard_append(f"{scheme}://localhost:{HECOS_PORT}/chat")
                root.update(); root.destroy()
            except Exception:
                pass
        threading.Thread(target=_do, daemon=True).start()

    def show_about(icon, item):
        def _do():
            try:
                import tkinter as tk
                from tkinter import messagebox
                root = tk.Tk(); root.withdraw()
                root.lift(); root.attributes('-topmost', True)
                msg = (
                    f"Hecos — v{version}\n"
                    f"Helping Companion System\n\n"
                    f"Created by: Antonio Meloni\n\n"
                    f"Status: {status_label}\n"
                    f"LAN: {scheme}://{lan_ip}:{HECOS_PORT}/chat"
                )
                messagebox.showinfo("About Hecos", msg, parent=root)
                root.destroy()
            except Exception:
                icon.notify(
                    f"Hecos — v{version}\nCreated by: Antonio Meloni\nStatus: {status_label}\nLAN: {scheme}://{lan_ip}:{HECOS_PORT}/chat",
                    "About Hecos"
                )
        threading.Thread(target=_do, daemon=True).start()

    # ── Browser submenu (dynamic, based on installed browsers) ───────────────

    browsers = discover_browsers()

    def _make_browser_opener(br_path):
        """Factory so each closure captures its own path."""
        def _open(icon, item):
            launch_browser(br_path, "")
        return _open

    browser_submenu_items = []
    if browsers:
        for br in browsers:
            browser_submenu_items.append(
                pystray.MenuItem(f"  {br['name']}", _make_browser_opener(br["path"]))
            )
    else:
        browser_submenu_items.append(
            pystray.MenuItem("  (No browsers found)", None, enabled=False)
        )

    # ── Settings submenu ─────────────────────────────────────────────────────

    settings_submenu = pystray.Menu(
        pystray.MenuItem(
            "Start Core with Tray",
            toggle_autostart,
            checked=lambda item: load_settings().get("start_hecos_on_launch", True),
        ),
        pystray.MenuItem(
            "Auto-open WebUI on startup",
            toggle_autoopen,
            checked=lambda item: load_settings().get("autoopen_webui", True),
        ),
        pystray.MenuItem(
            "Auto-open AI Browser (Playwright)",
            toggle_autoopen_ai_browser,
            checked=lambda item: load_settings().get("autoopen_ai_browser", False),
        ),
        pystray.MenuItem(
            "Auto-launch AI-Ready Chrome",
            toggle_auto_launch_chrome,
            checked=lambda item: load_settings().get("auto_launch_chrome_for_ai", False),
        ),
    )

    # ── AI Browser submenu ───────────────────────────────────────────────────

    ai_browser_submenu = pystray.Menu(
        pystray.MenuItem(f"🚀 Open AI-Ready Chrome  {ai_browser_status}", do_launch_ai_ready_browser),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("🌍 Open Browser", pystray.Menu(*browser_submenu_items)),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(
            "Auto-launch AI Chrome on startup",
            toggle_auto_launch_chrome,
            checked=lambda item: load_settings().get("auto_launch_chrome_for_ai", False),
        ),
    )

    # ── Technical / Debug submenu ────────────────────────────────────────────

    technical_submenu = pystray.Menu(
        pystray.MenuItem("🖥️  Launch Console", open_console),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(f"🖧  Copy LAN IP  ({lan_ip}:{HECOS_PORT})", copy_lan_ip),
        pystray.MenuItem(f"🔌 Copy WebUI URL", copy_local_url),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("ℹ️  About Hecos", show_about),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(
            "Show Technical Menu",
            toggle_technical_menu,
            checked=lambda item: load_settings().get("show_technical_menu", True),
        ),
    )

    # ── Root menu ────────────────────────────────────────────────────────────

    root_items = [
        pystray.MenuItem(f"HECOS  v{version}", None, enabled=False),
        pystray.MenuItem(status_label, None, enabled=False),
        pystray.Menu.SEPARATOR,

        # ── Web UI
        pystray.MenuItem("🌐 Open Chat", open_chat),
        pystray.MenuItem("⚙️  Central Hub", open_config),
        pystray.MenuItem("📱 Mobile (QR Code)", show_qr),
        pystray.Menu.SEPARATOR,

        # ── Core controls
        pystray.MenuItem("▶️  Start Core", start_core_btn),
        pystray.MenuItem("🔄 Restart Core", restart_core),
        pystray.MenuItem("⏹  Stop Core", stop_core),
        pystray.MenuItem("⏹  Stop Core + Quit Tray", stop_core_and_quit),
        pystray.Menu.SEPARATOR,

        # ── Browser / AI
        pystray.MenuItem("🤖 AI Browser & Chrome", ai_browser_submenu),
        pystray.Menu.SEPARATOR,

        # ── Settings
        pystray.MenuItem("⚙️  Settings", settings_submenu),
        pystray.Menu.SEPARATOR,
    ]

    # ── Advanced / Technical block —— only if enabled ────────────────────────
    if show_tech:
        root_items.append(pystray.MenuItem("🔧 Advanced / Debug", technical_submenu))
        root_items.append(pystray.Menu.SEPARATOR)
    else:
        # Minimal: just a "show technical" toggle
        root_items.append(
            pystray.MenuItem(
                "🔧 Show Technical Menu",
                toggle_technical_menu,
                checked=lambda item: load_settings().get("show_technical_menu", True),
            )
        )
        root_items.append(pystray.Menu.SEPARATOR)

    root_items.append(pystray.MenuItem("✖  Quit Tray", quit_tray))

    return pystray.Menu(*root_items)
