import os
import json

import sys

# Determine the root directory of the project
_fallback_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_exe_root = os.path.dirname(os.path.dirname(sys.executable))

# If running as the Nuitka compiled binary (C:\Hecos\bin\hecos_tray.exe), _exe_root will be C:\Hecos
if ("hecos_tray.exe" in sys.executable.lower() or "hecos_dashboard.exe" in sys.executable.lower()) and os.path.exists(os.path.join(_exe_root, "hecos", "assets")):
    _ROOT = _exe_root
else:
    _ROOT = _fallback_root

# === Configuration ===
HECOS_PORT = 7070
STATUS_POLL_INTERVAL = 3  # seconds (reduced for better responsiveness)
LOGO_PATH = os.path.join(_ROOT, "hecos", "assets", "Hecos_Logo_SQR_NBG_LogoOnly_Mask_001.ico")
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
    "use_daemon": False,              # launch Hecos under the Supervisor watchdog (auto-restart on crash)
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


# ─────────────────────────────────────────────────────────────
#  WebUI config (reads/writes plugins.yaml WEB_UI section)
# ─────────────────────────────────────────────────────────────

_WEBUI_DEFAULTS = {
    "port": 7070,
    "api_port": 5000,
    "https_enabled": False,
    "force_login": True,
    "auto_open_browser": False,
    "cert_file": "",
    "key_file": "",
}

def get_webui_config() -> dict:
    """Read the WEB_UI section from plugins.yaml."""
    try:
        import yaml
        with open(PLUGINS_YAML, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        webui = data.get("plugins", {}).get("WEB_UI", {})
        result = dict(_WEBUI_DEFAULTS)
        result.update({k: v for k, v in webui.items() if k in _WEBUI_DEFAULTS})
        return result
    except Exception as e:
        print(f"[TRAY] Could not read WebUI config: {e}")
        return dict(_WEBUI_DEFAULTS)


def save_webui_config(cfg: dict):
    """Write the WEB_UI section back to plugins.yaml, preserving the rest."""
    try:
        import yaml
        with open(PLUGINS_YAML, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        if "plugins" not in data:
            data["plugins"] = {}
        if "WEB_UI" not in data["plugins"]:
            data["plugins"]["WEB_UI"] = {}
        for k, v in cfg.items():
            data["plugins"]["WEB_UI"][k] = v
        with open(PLUGINS_YAML, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
    except Exception as e:
        print(f"[TRAY] Could not save WebUI config: {e}")

