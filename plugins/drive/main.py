"""
Plugin: Zentra Drive
HTTP File Manager — browse, upload, download and delete files via WebUI.
"""

import os

TAG = "DRIVE"

class DrivePlugin:
    """Zentra Drive — HTTP File Manager Plugin."""
    
    def __init__(self):
        self.tag = TAG
        self.desc = "HTTP File Manager: sfoglia, carica, scarica e cancella file via WebUI."
        self.config_schema = {
            "root_dir": {
                "type": "str",
                "default": "",
                "description": "Root directory del Drive (vuoto = home utente). Navigazione limitata a questa cartella."
            },
            "max_upload_mb": {
                "type": "int",
                "default": 100,
                "min": 1,
                "max": 2048,
                "description": "Dimensione massima upload in MB."
            },
            "allowed_extensions": {
                "type": "str",
                "default": "",
                "description": "Estensioni consentite in upload (vuoto = tutte). Esempio: jpg,png,pdf,txt"
            }
        }
        self.status = "ONLINE"

    def get_root(self):
        """Returns the configured root directory for the drive."""
        try:
            from app.config import ConfigManager
            cfg = ConfigManager()
            root = cfg.get_plugin_config(TAG, "root_dir", "")
        except Exception:
            root = ""
        
        if not root:
            root = os.path.expanduser("~")  # Default: home utente
        
        return os.path.abspath(root)

    def get_max_upload_bytes(self):
        try:
            from app.config import ConfigManager
            cfg = ConfigManager()
            mb = cfg.get_plugin_config(TAG, "max_upload_mb", 100)
        except Exception:
            mb = 100
        return int(mb) * 1024 * 1024

    def get_allowed_extensions(self):
        try:
            from app.config import ConfigManager
            cfg = ConfigManager()
            ext_str = cfg.get_plugin_config(TAG, "allowed_extensions", "")
        except Exception:
            ext_str = ""
        if not ext_str:
            return None  # All allowed
        return {e.strip().lstrip(".").lower() for e in ext_str.split(",") if e.strip()}


# Singleton
_plugin = DrivePlugin()


# --- Plugin standard interface ---
def info():
    return {
        "tag": _plugin.tag,
        "desc": _plugin.desc,
        "commands": {
            "/drive": "Apre il File Manager nel browser",
        },
        "example": "Vai su /drive per sfogliare i tuoi file."
    }

def status():
    root = _plugin.get_root()
    return "ONLINE" if os.path.isdir(root) else "ERROR"

def get_plugin():
    return _plugin
