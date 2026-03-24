import os
import re
from core.logging import logger
from core.i18n import translator
from app.config import ConfigManager

def info():
    return {
        "tag": "FILE_MANAGER",
        "desc": translator.t("plugin_file_manager_desc"),
        "comandi": {
            "list:path": translator.t("plugin_file_manager_list_desc"),
            "count:path": translator.t("plugin_file_manager_conta_desc"),
            "read:path": translator.t("plugin_file_manager_read_desc")
        }
    }

def status():
    return "ONLINE"

def config_schema():
    """
    Schema di configurazione per questo plugin.
    """
    return {
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

def _espandi_percorso(target):
    """
    Converte un target simbolico in percorso assoluto.
    """
    cfg_mgr = ConfigManager()

    if not cfg_mgr.get_plugin_config("FILE_MANAGER", "enable_path_mapping", True):
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

    custom_mappings = cfg_mgr.get_plugin_config("FILE_MANAGER", "mappings", {})
    mapping = {**default_mapping, **custom_mappings}

    return mapping.get(target, target)

def esegui(comando):
    logger.debug("PLUGIN_FILE_MANAGER", f"esegui() chiamato con comando: '{comando}'")

    cfg_mgr = ConfigManager()
    max_read_lines = cfg_mgr.get_plugin_config("FILE_MANAGER", "max_read_lines", 50)
    max_list_items = cfg_mgr.get_plugin_config("FILE_MANAGER", "max_list_items", 5)

    cmd = comando.lower().strip()

    # Gestione list:
    if cmd.startswith("list:"):
        target = cmd[5:].strip()
        path = _espandi_percorso(target)
        logger.debug("PLUGIN_FILE_MANAGER", f"list: target={target}, path={path}")

        try:
            if os.path.exists(path):
                elementi = os.listdir(path)
                cartelle = [f for f in elementi if os.path.isdir(os.path.join(path, f))]
                files = [f for f in elementi if os.path.isfile(os.path.join(path, f))]
                
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
                return translator.t("plugin_file_manager_not_found", path=path)
        except Exception as e:
            return f"Error: {e}"

    # Gestione count: / conta:
    elif cmd.startswith("count:") or cmd.startswith("conta:"):
        prefix_len = 6 if cmd.startswith("count:") else 6
        target = cmd[prefix_len:].strip()
        path = _espandi_percorso(target)

        try:
            if os.path.exists(path):
                elementi = os.listdir(path)
                cartelle = [f for f in elementi if os.path.isdir(os.path.join(path, f))]
                files = [f for f in elementi if os.path.isfile(os.path.join(path, f))]
                return translator.t("plugin_file_manager_count_res", target=target, folders=len(cartelle), files=len(files))
            else:
                return translator.t("plugin_file_manager_not_found", path=path)
        except Exception as e:
            return f"Error: {e}"

    # Gestione read:
    elif cmd.startswith("read:"):
        target = cmd[5:].strip()
        path = _espandi_percorso(target)

        try:
            if os.path.isfile(path):
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    total = len(lines)
                    mostra = lines[:max_read_lines]

                    if total > max_read_lines:
                        header = translator.t("plugin_file_manager_read_header_full", target=target, lines=max_read_lines, total=total)
                    else:
                        header = translator.t("plugin_file_manager_read_header", target=target, lines=total)
                    
                    return header + "\n" + "".join(mostra)
            else:
                return translator.t("plugin_file_manager_not_file", path=path)
        except Exception as e:
            return f"Error: {e}"

    return translator.t("plugin_file_manager_cmd_unknown")