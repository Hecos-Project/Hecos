import os
try:
    from core.logging import logger
    from core.i18n import translator
    from app.config import ConfigManager
except ImportError:
    class DummyLogger:
        def debug(self, *args, **kwargs): print("[FM_DEBUG]", *args)
        def error(self, *args, **kwargs): print("[FILE_ERR]", *args)
    logger = DummyLogger()
    class DummyTranslator:
        def t(self, key, **kwargs): return key
    translator = DummyTranslator()
    class DummyConfigMgr:
        def __init__(self): self.config = {}
        def get_plugin_config(self, tag, key, default): return default
    ConfigManager = DummyConfigMgr

class FileManager:
    """
    Plugin: File Manager
    Tools for interaction with the local file system.
    Allows listing folders, counting files, and reading the content of text documents.
    """

    def __init__(self):
        self.tag = "FILE_MANAGER"
        self.desc = translator.t("plugin_file_manager_desc")
        self.config_schema = {
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
            },
            "enable_path_mapping": {
                "type": "bool",
                "default": True,
                "description": translator.t("plugin_file_manager_enable_path_mapping_desc")
            }
        }
        self.status = "ONLINE"

    def _expand_path(self, target: str) -> str:
        """
        Converts a symbolic target (e.g., 'desktop') to an absolute path.
        
        :param target: The symbolic or absolute path to expand.
        :return: The calculated absolute path.
        """
        cfg_mgr = ConfigManager()

        if not cfg_mgr.get_plugin_config(self.tag, "enable_path_mapping", True):
            return target

        user_path = os.path.expanduser("~")
        cwd = os.getcwd()

        default_mapping = {
            "desktop": os.path.join(user_path, "Desktop"),
            "documents": os.path.join(user_path, "Documents"),
            "download": os.path.join(user_path, "Downloads"),
            "core": os.path.join(cwd, "core"),
            "plugins": os.path.join(cwd, "plugins"),
            "memory": os.path.join(cwd, "memory"),
            "personality": os.path.join(cwd, "personality"),
            "logs": os.path.join(cwd, "logs"),
            "config": os.path.join(cwd, "config.json"),
            "main": os.path.join(cwd, "main.py"),
        }

        custom_mappings = cfg_mgr.get_plugin_config(self.tag, "mappings", {})
        mapping = {**default_mapping, **custom_mappings}

        return mapping.get(target, target)

    def list_files(self, path: str) -> str:
        """
        SCANS and lists files/folders in a path to return the names to the AI.
        Use this tool ONLY if you need to know the filenames to process them or answer questions. 
        Does NOT open a visual window for the user.
        
        :param path: The path of the directory to inspect (e.g., 'desktop' or an absolute path).
        :return: A summary string with the folder content.
        """
        target = path.strip()
        espanso = self._expand_path(target)
        logger.debug(f"PLUGIN_{self.tag}", f"list: target={target}, path={espanso}")

        cfg_mgr = ConfigManager()
        max_list_items = cfg_mgr.get_plugin_config(self.tag, "max_list_items", 5)

        try:
            if os.path.exists(espanso):
                elementi = os.listdir(espanso)
                cartelle = [f for f in elementi if os.path.isdir(os.path.join(espanso, f))]
                files = [f for f in elementi if os.path.isfile(os.path.join(espanso, f))]
                
                res = translator.t("plugin_file_manager_analysis", target=target)
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
        Counts the total number of files and folders in a given path, without listing them.
        
        :param path: The path of the directory to inspect.
        :return: A string with the count of elements.
        """
        target = path.strip()
        espanso = self._expand_path(target)

        try:
            if os.path.exists(espanso):
                elementi = os.listdir(espanso)
                cartelle = [f for f in elementi if os.path.isdir(os.path.join(espanso, f))]
                files = [f for f in elementi if os.path.isfile(os.path.join(espanso, f))]
                return translator.t("plugin_file_manager_count_res", target=target, folders=len(cartelle), files=len(files))
            else:
                return translator.t("plugin_file_manager_not_found", path=espanso)
        except Exception as e:
            return f"Error: {e}"

    def read_file(self, path: str) -> str:
        """
        Reads the textual content of a file specified by the path.
        If the file is very long, it only reads an initial part defined in settings.
        
        :param path: The path of the text file to read.
        :return: The first lines of the file as text.
        """
        target = path.strip()
        espanso = self._expand_path(target)

        cfg_mgr = ConfigManager()
        max_read_lines = cfg_mgr.get_plugin_config(self.tag, "max_read_lines", 50)

        try:
            if os.path.isfile(espanso):
                with open(espanso, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    total = len(lines)
                    mostra = lines[:max_read_lines]

                    if total > max_read_lines:
                        header = translator.t("plugin_file_manager_read_header_full", target=target, lines=max_read_lines, total=total)
                    else:
                        header = translator.t("plugin_file_manager_read_header", target=target, lines=total)
                    
                    return header + "\n" + "".join(mostra)
            else:
                return translator.t("plugin_file_manager_not_file", path=espanso)
        except Exception as e:
            return f"Error: {e}"

# Istanzia pubblicamente lo strumento per l'esportazione verso il Core
tools = FileManager()

# --- COMPATIBILITY SHIMS ---
def info():
    return {"tag": tools.tag, "desc": tools.desc}

def status():
    return tools.status

def execute(comando: str) -> str:
    """Compatibilità legacy: smista i comandi testuali ai nuovi metodi ad oggetti."""
    c = comando.strip()
    c_lower = c.lower()
    
    if c_lower.startswith("list:") or c_lower.startswith("lista:") or c_lower.startswith("list_files:"):
        path = c.split(":", 1)[1].strip()
        return tools.list_files(path)
    elif c_lower.startswith("count:") or c_lower.startswith("conta:") or c_lower.startswith("count_items:"):
        path = c.split(":", 1)[1].strip()
        return tools.count_items(path)
    elif c_lower.startswith("read:") or c_lower.startswith("leggi:") or c_lower.startswith("read_file:"):
        path = c.split(":", 1)[1].strip()
        return tools.read_file(path)
        
    return f"Errore: Comando legacy '{comando}' non supportato o mancante. Usa Tools Calling."