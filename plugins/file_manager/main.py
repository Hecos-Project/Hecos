import os
import re
from core import logger

def info():
    return {
        "tag": "FILE_MANAGER",
        "desc": "Gestione file e directory di sistema con supporto ai percorsi utente e lettura file.",
        "comandi": {
            "list:percorso": "Elenca file e cartelle (es. list:desktop, list:core, list:plugins).",
            "conta:percorso": "Fornisce un conteggio dettagliato degli elementi in una cartella.",
            "read:percorso": "Legge il contenuto di un file di testo (prime 50 righe)."
        }
    }

def _espandi_percorso(target):
    """Converte un target simbolico in percorso assoluto."""
    user_path = os.path.expanduser("~")
    cwd = os.getcwd()
    mapping = {
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
    return mapping.get(target, target)

def esegui(comando):
    logger.debug("PLUGIN_FILE_MANAGER", f"esegui() chiamato con comando: '{comando}'")
    
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
                if cartelle:
                    res += f"\nPrime cartelle: {', '.join(cartelle[:5])}"
                if files:
                    res += f"\nPrimi file: {', '.join(files[:5])}"
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
                    mostra = lines[:50]
                    logger.debug("PLUGIN_FILE_MANAGER", f"Lette {total} righe, mostrate prime 50")
                    
                    if total > 50:
                        res = f"File '{target}' (prime 50 righe su {total}):\n" + "".join(mostra)
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