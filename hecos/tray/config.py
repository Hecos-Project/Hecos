import os
import sys
import tomllib
import tomli_w

# ─────────────────────────────────────────────────────────────
#  Root detection
# ─────────────────────────────────────────────────────────────
_fallback_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_is_compiled = getattr(sys, 'frozen', False) or (
    "__file__" in dir() and
    (os.path.abspath(__file__).lower().endswith("hecos_tray.exe") or
     os.path.abspath(__file__).lower().endswith("hecos_dashboard.exe"))
)

if _is_compiled:
    _ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if not os.path.exists(os.path.join(_ROOT, "hecos", "assets")):
        _ROOT = _fallback_root
else:
    _ROOT = _fallback_root

# Tray config directory — all tray-specific config lives here
_TRAY_DIR = os.path.join(_ROOT, "hecos", "tray")

# ─────────────────────────────────────────────────────────────
#  Path constants
# ─────────────────────────────────────────────────────────────
HECOS_PORT          = 7070
STATUS_POLL_INTERVAL = 3  # seconds

LOGO_PATH           = os.path.join(_ROOT, "hecos", "assets", "Hecos_Logo_SQR_NBG_LogoOnly_Mask_001.ico")
VERSION_FILE        = os.path.join(_ROOT, "hecos", "core", "version")
SYSTEM_YAML         = os.path.join(_ROOT, "hecos", "config", "data", "system.yaml")
PLUGINS_YAML        = os.path.join(_ROOT, "hecos", "config", "data", "plugins.yaml")

# Settings and update sources now live alongside the tray source code
SETTINGS_FILE       = os.path.join(_TRAY_DIR, "tray_settings.toml")
UPDATE_SOURCES_FILE = os.path.join(_TRAY_DIR, "update_sources.toml")


# ─────────────────────────────────────────────────────────────
#  Settings — default values
# ─────────────────────────────────────────────────────────────
_DEFAULTS: dict = {
    "start_hecos_on_launch":    False,  # launch Hecos python subprocess at tray startup
    "autoopen_webui":           False,  # open the browser automatically when service comes online
    "autoopen_ai_browser":      False,  # open Playwright Chromium browser when service comes online
    "auto_launch_chrome_for_ai": False, # auto-launch Chrome in AI-Ready (CDP) mode on startup
    "browser_startup_url":      "http://localhost:7070",
    "browser_headless":         False,  # True = AI browser runs invisibly in background
    "show_technical_menu":      True,   # show Advanced/Debug submenu in tray
    "use_daemon":               False,  # launch Hecos under the Supervisor watchdog
    "full_color_logs":          False,
}

_TOML_HEADER = """\
# Hecos Tray — Settings
# ─────────────────────────────────────────────────────────────
# This file is read on every tray startup.
# You can edit it with any text editor while the tray is closed.
# Boolean values: true / false   |   Strings must be in "quotes"
# ─────────────────────────────────────────────────────────────

"""

_TOML_COMMENTS = {
    "start_hecos_on_launch":    "# Launch the Hecos core service automatically when the tray starts",
    "autoopen_webui":           "# Open the web browser to the Hecos UI when the service comes online",
    "autoopen_ai_browser":      "# Open the built-in AI browser (Playwright) on service startup",
    "auto_launch_chrome_for_ai":"# Launch Chrome in CDP/AI-ready mode on tray startup",
    "browser_startup_url":      "# URL to open when the browser or WebUI auto-launch",
    "browser_headless":         "# true = AI browser runs hidden in the background",
    "show_technical_menu":      "# Show the Advanced / Debug submenu in the tray icon menu",
    "use_daemon":               "# Run Hecos under the Supervisor watchdog (auto-restart on crash)",
    "full_color_logs":          "# Enable full ANSI colour output in the live-log tab",
}


def _write_toml_settings(data: dict, path: str):
    """Write settings to a TOML file, preserving human-readable comments."""
    lines = [_TOML_HEADER]
    for key, value in data.items():
        comment = _TOML_COMMENTS.get(key, "")
        if comment:
            lines.append(comment)
        if isinstance(value, bool):
            lines.append(f"{key} = {str(value).lower()}")
        elif isinstance(value, str):
            lines.append(f'{key} = "{value}"')
        else:
            lines.append(f"{key} = {value}")
        lines.append("")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def load_settings() -> dict:
    try:
        with open(SETTINGS_FILE, "rb") as f:
            data = tomllib.load(f)
        for k, v in _DEFAULTS.items():
            data.setdefault(k, v)
        return data
    except Exception:
        return dict(_DEFAULTS)


def save_settings(settings: dict):
    try:
        os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
        _write_toml_settings(settings, SETTINGS_FILE)
    except Exception as e:
        print(f"[TRAY] Could not save settings: {e}")


# ─────────────────────────────────────────────────────────────
#  WebUI config  (reads / writes plugins.yaml  WEB_UI section)
# ─────────────────────────────────────────────────────────────
_WEBUI_DEFAULTS = {
    "port":             7070,
    "api_port":         5000,
    "https_enabled":    False,
    "force_login":      True,
    "auto_open_browser": False,
    "cert_file":        "",
    "key_file":         "",
}


def get_webui_config() -> dict:
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
    try:
        import yaml
        with open(PLUGINS_YAML, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        data.setdefault("plugins", {}).setdefault("WEB_UI", {})
        for k, v in cfg.items():
            data["plugins"]["WEB_UI"][k] = v
        with open(PLUGINS_YAML, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
    except Exception as e:
        print(f"[TRAY] Could not save WebUI config: {e}")
