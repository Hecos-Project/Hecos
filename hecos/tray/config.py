import os
import json

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# === Configuration ===
HECOS_PORT = 7070
STATUS_POLL_INTERVAL = 3  # seconds (reduced for better responsiveness)
LOGO_PATH = os.path.join(_ROOT, "hecos", "assets", "Hecos_Logo_SQR_NBG_LogoOnly.png")
VERSION_FILE = os.path.join(_ROOT, "hecos", "core", "version")
SYSTEM_YAML = os.path.join(_ROOT, "hecos", "config", "data", "system.yaml")
PLUGINS_YAML = os.path.join(_ROOT, "hecos", "config", "data", "plugins.yaml")
SETTINGS_FILE = os.path.join(_ROOT, "hecos_tray_settings.json")


# ─────────────────────────────────────────────────────────────
#  Settings persistence
# ─────────────────────────────────────────────────────────────

_DEFAULTS = {
    "start_hecos_on_launch": True,    # launch Hecos python subprocess at tray startup
    "autoopen_webui": True,           # open the browser automatically when service comes online
    "autoopen_ai_browser": False,     # open Playwright Chromium browser when service comes online
    "auto_launch_chrome_for_ai": False,  # auto-launch Chrome in AI-Ready (CDP) mode on startup
    "browser_startup_url": "http://localhost:7070",  # URL to open automatically when AI browser launches
    "browser_headless": False,        # True = AI browser runs invisibly in background
    "show_technical_menu": True,      # show Advanced/Debug submenu in tray
}

def load_settings() -> dict:
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Fill any missing keys with defaults
        for k, v in _DEFAULTS.items():
            data.setdefault(k, v)
        return data
    except Exception:
        return dict(_DEFAULTS)


def save_settings(settings: dict):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        print(f"[TRAY] Could not save settings: {e}")
