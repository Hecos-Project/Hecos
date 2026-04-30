import os
try:
    from hecos.core.logging import logger
    from hecos.core.i18n import translator
    from app.config import ConfigManager
except ImportError:
    class DummyLogger:
        def debug(self, *args, **kwargs): print("[DRIVE_DEBUG]", *args)
        def error(self, *args, **kwargs): print("[DRIVE_ERR]", *args)
        def info(self, *args, **kwargs): print("[DRIVE_INFO]", *args)
    logger = DummyLogger()
    class DummyTranslator:
        def t(self, key, **kwargs): return key
    translator = DummyTranslator()
    class DummyConfigMgr:
        def __init__(self): self.config = {}
        def get_plugin_config(self, tag, key, default): return default
    ConfigManager = DummyConfigMgr

TAG = "DRIVE"

class DrivePlugin:
    """Hecos Drive — HTTP File Manager Plugin."""
    
    def __init__(self):
        self.tag = TAG
        self.desc = translator.t("webui_desc_drive") or "Hecos Drive: Gestione file avanzata via WebUI (Upload, Download, Editor)."
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
            "max_read_lines": {
                "type": "int",
                "default": 50,
                "min": 1,
                "max": 500,
                "description": translator.t("plugin_file_manager_max_read_lines_desc")
            },
            "max_list_items": {
                "type": "int",
                "default": 5,
                "min": 0,
                "max": 20,
                "description": translator.t("plugin_file_manager_max_list_items_desc")
            }
        }
        self.status = "ONLINE"

    def get_root(self):
        """Returns the configured root directory for the drive."""
        cfg = ConfigManager()
        root = cfg.get_plugin_config(TAG, "root_dir", "")
        if not root:
            import sys
            root = "C:\\" if sys.platform == "win32" else "/"
        return os.path.abspath(root)

    def _expand_path(self, target: str) -> str:
        target = target.strip()
        user_path = os.path.expanduser("~")
        hecos_root = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))

        # Mapping legacy aliases for consistency
        mapping = {
            "desktop": os.path.join(user_path, "Desktop"),
            "documents": os.path.join(user_path, "Documents"),
            "download": os.path.join(user_path, "Downloads"),
            "core": os.path.join(hecos_root, "core"),
            "plugins": os.path.join(hecos_root, "plugins"),
            "memory": os.path.join(hecos_root, "memory"),
            "personality": os.path.join(hecos_root, "personality"),
            "logs": os.path.join(hecos_root, "logs"),
            "config": os.path.join(hecos_root, "config", "data", "system.yaml"),
            "main": os.path.join(os.path.dirname(hecos_root), "main.py"),
        }
        return mapping.get(target.lower(), target)

    def list_files(self, path: str) -> str:
        """
        SCANS and lists files/folders in a path to return the names to the AI.
        
        :param path: The path of the directory to inspect (e.g., 'desktop' or an absolute path).
        """
        espanso = self._expand_path(path)
        cfg_mgr = ConfigManager()
        max_list_items = cfg_mgr.get_plugin_config(self.tag, "max_list_items", 5)

        try:
            if os.path.exists(espanso):
                elementi = os.listdir(espanso)
                cartelle = [f for f in elementi if os.path.isdir(os.path.join(espanso, f))]
                files = [f for f in elementi if os.path.isfile(os.path.join(espanso, f))]
                
                res = translator.t("plugin_file_manager_analysis", target=path)
                res += f"\n- " + translator.t("plugin_file_manager_folders", count=len(cartelle))
                res += f"\n- " + translator.t("plugin_file_manager_files", count=len(files))
                
                if max_list_items > 0:
                    if cartelle:
                        list_str = ", ".join(cartelle[:max_list_items])
                        res += f"\n" + translator.t("plugin_file_manager_folders_list", list=list_str)
                    if files:
                        list_str = ", ".join(files[:max_list_items])
                        res += f"\n" + translator.t("plugin_file_manager_files_list", list=list_str)
                return res
            else:
                return translator.t("plugin_file_manager_not_found", path=espanso)
        except Exception as e:
            return f"Error: {e}"

    def count_items(self, path: str) -> str:
        """
        Counts the total number of files and folders in a given path.
        """
        espanso = self._expand_path(path)
        try:
            if os.path.exists(espanso):
                elementi = os.listdir(espanso)
                cartelle = [f for f in elementi if os.path.isdir(os.path.join(espanso, f))]
                files = [f for f in elementi if os.path.isfile(os.path.join(espanso, f))]
                return translator.t("plugin_file_manager_count_res", target=path, folders=len(cartelle), files=len(files))
            else:
                return translator.t("plugin_file_manager_not_found", path=espanso)
        except Exception as e:
            return f"Error: {e}"

    def read_file(self, path: str) -> str:
        """
        Reads the textual content of a file.
        """
        espanso = self._expand_path(path)
        cfg_mgr = ConfigManager()
        max_read_lines = cfg_mgr.get_plugin_config(self.tag, "max_read_lines", 50)

        try:
            if os.path.isfile(espanso):
                with open(espanso, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    total = len(lines)
                    mostra = lines[:max_read_lines]
                    header = translator.t("plugin_file_manager_read_header_full", target=path, lines=len(mostra), total=total)
                    return header + "\n" + "".join(mostra)
            else:
                return translator.t("plugin_file_manager_not_file", path=espanso)
        except Exception as e:
            return f"Error: {e}"

# Singleton
tools = DrivePlugin()

# --- Plugin standard interface ---
def info():
    return {
        "tag": tools.tag,
        "desc": tools.desc,
        "commands": {
            "list_files": "Sfoglia i file in una cartella locale.",
            "read_file": "Leggi il contenuto di un file di testo.",
            "count_items": "Conta elementi in un percorso.",
            "/drive": "Apre il File Manager nel browser"
        }
    }

def status():
    return tools.status

def get_plugin():
    return tools
