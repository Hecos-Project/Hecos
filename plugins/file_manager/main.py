import os
import re
from core.logging import logger
from app.config import ConfigManager  # <--- nuovo import

def info():
    return {
        "tag": "FILE_MANAGER",
        "desc": "Gestione file e directory di sistema con supporto ai percorsi utente e lettura file.",
        "comandi": {
            "list:percorso": "Elenca file e cartelle (es. list:desktop, list:core, list:plugins).",
            "conta:percorso": "Fornisce un conteggio dettagliato degli elementi in una cartella.",
            "read:percorso": "Legge il contenuto di un file di testo (prime righe configurabili)."
        }
    }

def status():
    return "ATTIVO"

def config_schema():
    """
    Schema di configurazione per questo plugin.
    I valori qui definiti verranno aggiunti automaticamente in config.json
    nella sezione plugins.FILE_MANAGER.
    """
    return {
        "max_read_lines": {
            "type": "int",
            "default": 50,
            "min": 1,
            "max": 500,
            "description": "Numero massimo di righe da mostrare quando si legge un file"
        },
        "max_list_items": {
            "type": "int",
            "default": 5,
            "min": 0,
            "max": 20,
            "description": "Numero massimo di elementi da elencare (0 = nessun elenco)"
        },
        "enable_path_mapping": {
            "type": "bool",
            "default": True,
            "description": "Abilita la mappatura dei percorsi simbolici (desktop, core, ecc.)"
        }
    }

def _espandi_percorso(target):
    """
    Converte un target simbolico in percorso assoluto.
    Ora legge i mapping da config.json per personalizzabilità.
    """
    # Ottieni la configurazione centralizzata
    cfg_mgr = ConfigManager()

    # Se la mappatura è disabilitata, restituisci il target così com'è
    if not cfg_mgr.get_plugin_config("FILE_MANAGER", "enable_path_mapping", True):
        return target

    user_path = os.path.expanduser("~")
    cwd = os.getcwd()

    # Mappa di default (usata se non diversamente specificato in config)
    default_mapping = {
        "desktop": os.path.join(user_path, "Desktop"),
        "documenti": os.path.join(user_path, "Documents"),
        "download": os.path.join(user_path, "Downloads"),
        "core": os.path.join(cwd, "core"),
        "plugins": os.path.join(cwd, "plugins"),
        "memoria": os.path.join(cwd, "memoria"),
        "personalita": os.path.join(cwd, "personalita"),
        "logs": os.path.join(cwd, "logs"),
        "config": os.path.join(cwd, "config.json"),
        "main": os.path.join(cwd, "main.py"),
    }

    # Leggi eventuali mapping personalizzati dal config (sezione plugins.FILE_MANAGER.mappings)
    custom_mappings = cfg_mgr.get_plugin_config("FILE_MANAGER", "mappings", {})
    mapping = {**default_mapping, **custom_mappings}

    return mapping.get(target, target)

def esegui(comando):
    logger.debug("PLUGIN_FILE_MANAGER", f"esegui() chiamato con comando: '{comando}'")

    # Ottieni la configurazione per i limiti
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
                logger.debug("PLUGIN_FILE_MANAGER", f"Trovate {len(cartelle)} cartelle, {len(files)} file")

                res = f"Analisi di '{target}':\n- Cartelle: {len(cartelle)}\n- File: {len(files)}"
                if max_list_items > 0:
                    if cartelle:
                        res += f"\nPrime cartelle: {', '.join(cartelle[:max_list_items])}"
                    if files:
                        res += f"\nPrimi file: {', '.join(files[:max_list_items])}"
                return res
            else:
                logger.debug("PLUGIN_FILE_MANAGER", f"Percorso '{path}' non trovato")
                return f"Percorso '{path}' non trovato."
        except Exception as e:
            logger.debug("PLUGIN_FILE_MANAGER", f"Errore accesso: {e}")
            return f"Errore accesso: {e}"

    # Gestione conta:
    elif cmd.startswith("conta:"):
        target = cmd[6:].strip()
        path = _espandi_percorso(target)
        logger.debug("PLUGIN_FILE_MANAGER", f"conta: target={target}, path={path}")

        try:
            if os.path.exists(path):
                elementi = os.listdir(path)
                cartelle = [f for f in elementi if os.path.isdir(os.path.join(path, f))]
                files = [f for f in elementi if os.path.isfile(os.path.join(path, f))]
                logger.debug("PLUGIN_FILE_MANAGER", f"Conteggio: {len(cartelle)} cartelle, {len(files)} file")
                return f"Conteggio in '{target}': {len(cartelle)} cartelle, {len(files)} file."
            else:
                logger.debug("PLUGIN_FILE_MANAGER", f"Percorso '{path}' non trovato")
                return f"Percorso '{path}' non trovato."
        except Exception as e:
            logger.debug("PLUGIN_FILE_MANAGER", f"Errore accesso: {e}")
            return f"Errore accesso: {e}"

    # Gestione read:
    elif cmd.startswith("read:"):
        target = cmd[5:].strip()
        path = _espandi_percorso(target)
        logger.debug("PLUGIN_FILE_MANAGER", f"read: target={target}, path={path}")

        try:
            if os.path.isfile(path):
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    total = len(lines)
                    mostra = lines[:max_read_lines]
                    logger.debug("PLUGIN_FILE_MANAGER", f"Lette {total} righe, mostrate prime {max_read_lines}")

                    if total > max_read_lines:
                        res = f"File '{target}' (prime {max_read_lines} righe su {total}):\n" + "".join(mostra)
                    else:
                        res = f"File '{target}' ({total} righe):\n" + "".join(mostra)
                    return res
            else:
                logger.debug("PLUGIN_FILE_MANAGER", f"'{path}' non è un file o non esiste")
                return f"'{path}' non è un file o non esiste."
        except Exception as e:
            logger.debug("PLUGIN_FILE_MANAGER", f"Errore lettura file: {e}")
            return f"Errore lettura file: {e}"

    logger.debug("PLUGIN_FILE_MANAGER", "Comando non riconosciuto")
    return "Comando FILE_MANAGER non riconosciuto. Usa list:, conta: o read:"