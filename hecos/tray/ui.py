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
from hecos.tray.network_utils import get_scheme, get_urls, get_lan_ip, is_hecos_online
from hecos.tray.system_utils import play_beep, launch_console, terminate_consoles, get_version
from hecos.tray.browser_manager import (
    get_cdp_alive, discover_browsers, launch_browser,
    launch_ai_ready_browser, _get_cdp_port,
    intelligent_open_webui, intelligent_open_ai_browser,
    open_ai_browser, close_ai_browser
)
from hecos.tray.orchestrator import start_hecos, stop_hecos, restart_hecos
from hecos.tray.control_center import show_control_center


def load_icon(online: bool) -> "Image.Image":
    # Colors for the masked "H"
    # Success Green for Online, Warning Red for Offline
    accent = (0, 208, 122, 255) if online else (239, 68, 68, 255)
    
    try:
        if os.path.exists(LOGO_PATH):
            # Load the icon as a mask (with H transparent)
            img = Image.open(LOGO_PATH).convert("RGBA").resize((64, 64))
            # Create a solid background based on status
            bg = Image.new("RGBA", img.size, accent)
            # Composite: Logo ON TOP of background. 
            # Transparent 'H' in legacy logo will show the bg color.
            return Image.alpha_composite(bg, img)
    except Exception as e:
        print(f"[TRAY] Icon load error: {e}")
        pass

    # Generic fallback
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([4, 4, size - 4, size - 4], fill=accent)
    return img


def refresh_ui(icon: "pystray.Icon"):
    if not icon:
        return
    online = is_hecos_online()
    icon.icon = load_icon(online)
    icon.menu = build_menu([icon])


def build_menu(icon_ref: list):
    """
    Lean native tray right-click menu.
    All detailed controls live in the Control Center (left-click or top button).
    """
    settings  = load_settings()
    online    = is_hecos_online()
    version   = get_version()
    scheme    = get_scheme()
    _, _      = get_urls()
    status_label = "🟢 Online" if online else "🔴 Offline"
    show_tech    = settings.get("show_technical_menu", True)

    icon = icon_ref[0]

    def open_cc(i, it):
        show_control_center(i, it)

    def open_chat(i, it):
        intelligent_open_webui(i, it)

    def open_config(i, it):
        _, config_url = get_urls()
        webbrowser.open(config_url)

    def start_core_btn(i, it):
        def _do():
            play_beep(400, 100)
            start_hecos()
            time.sleep(2)
            refresh_ui(icon)
        threading.Thread(target=_do, daemon=True).start()

    def restart_core(i, it):
        def _do():
            play_beep(400, 100)
            play_beep(300, 150)
            terminate_consoles()
            restart_hecos()
            time.sleep(2)
            refresh_ui(icon)
        threading.Thread(target=_do, daemon=True).start()

    def stop_core(i, it):
        def _do():
            play_beep(400, 100)
            play_beep(300, 150)
            terminate_consoles()
            stop_hecos()
            time.sleep(1.5)
            refresh_ui(icon)
        threading.Thread(target=_do, daemon=True).start()

    def stop_core_and_quit(i, it):
        def _do():
            play_beep(400, 100)
            play_beep(300, 150)
            stop_hecos()
            time.sleep(1)
            icon.stop()
        threading.Thread(target=_do, daemon=True).start()

    def quit_tray(i, it):
        terminate_consoles()
        stop_hecos()
        icon.stop()

    def open_console(i, it):
        script = os.path.join(
            _ROOT, "scripts",
            "windows" if sys.platform == "win32" else "linux",
            "run",
            "HECOS_CONSOLE_RUN_WIN.bat" if sys.platform == "win32" else "HECOS_CONSOLE_RUN.sh"
        )
        launch_console(script)

    def toggle_technical_menu(i, it):
        s = load_settings()
        s["show_technical_menu"] = not s.get("show_technical_menu", True)
        save_settings(s)
        icon.menu = build_menu([icon])

    technical_submenu = pystray.Menu(
        pystray.MenuItem("🖥️  Launch Console", open_console),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Show Technical Menu", toggle_technical_menu,
                         checked=lambda it: load_settings().get("show_technical_menu", True)),
    )

    root_items = [
        pystray.MenuItem(f"HECOS  v{version}", None, enabled=False),
        pystray.MenuItem(status_label, None, enabled=False),
        pystray.Menu.SEPARATOR,
        # ── Main entry points
        pystray.MenuItem("🖥️  Control Center", open_cc),
        pystray.MenuItem("🌐 Open Chat", open_chat),
        pystray.MenuItem("⚙️  Central Hub", open_config),
        pystray.Menu.SEPARATOR,
        # ── Core lifecycle
        pystray.MenuItem("▶️  Start Core", start_core_btn),
        pystray.MenuItem("🔄 Restart Core", restart_core),
        pystray.MenuItem("⏹  Stop Core", stop_core),
        pystray.MenuItem("⏹  Stop Core + Quit Tray", stop_core_and_quit),
        pystray.Menu.SEPARATOR,
    ]

    if show_tech:
        root_items.extend([
            pystray.MenuItem("🔧 Advanced / Debug", technical_submenu),
            pystray.Menu.SEPARATOR,
        ])
    else:
        root_items.extend([
            pystray.MenuItem("🔧 Show Technical Menu", toggle_technical_menu,
                             checked=lambda it: load_settings().get("show_technical_menu", True)),
            pystray.Menu.SEPARATOR,
        ])

    root_items.append(pystray.MenuItem("✖  Quit Tray", quit_tray))

    return pystray.Menu(*root_items)
