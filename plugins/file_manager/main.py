import os
try:
    from core.logging import logger
    from core.i18n import translator
    from app.config import ConfigManager
except ImportError:
    class DummyLogger:
        def debug(self, *args, **kwargs): print("[FM_DEBUG]", *args)
        def errore(self, *args, **kwargs): print("[FM_ERR]", *args)
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
    Strumenti per l'interazione con il file system locale.
    Permette di elencare cartelle, contare file e leggere il contenuto di documenti testuali.
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

    def _espandi_percorso(self, target: str) -> str:
        """
        Converte un target simbolico (es. 'desktop') in un percorso assoluto.
        
        :param target: Il percorso simbolico o assoluto da espandere.
        :return: Il percorso assoluto calcolato.
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
        Elenca le cartelle e i file presenti in un determinato percorso.
        
        :param path: Il percorso della directory da ispezionare (es. 'desktop' o un percorso assoluto).
        :return: Una stringa riassuntiva con il contenuto della cartella.
        """
        target = path.strip()
        espanso = self._espandi_percorso(target)
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
        Conta il numero totale di file e cartelle in un dato percorso, senza elencarli.
        
        :param path: Il percorso della directory da ispezionare.
        :return: Una stringa con il conteggio degli elementi.
        """
        target = path.strip()
        espanso = self._espandi_percorso(target)

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
        Legge il contenuto testuale di un file specificato dal percorso.
        Se il file è molto lungo, ne legge solo una parte iniziale definita nelle impostazioni.
        
        :param path: Il percorso del file testuale da leggere.
        :return: Le prime righe del file come testo.
        """
        target = path.strip()
        espanso = self._espandi_percorso(target)

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