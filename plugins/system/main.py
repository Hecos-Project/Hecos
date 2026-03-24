"""Modulo principale del plugin System."""
import sys
import subprocess
import os
import winsound
import time
import re
import datetime
import json
from core.logging import logger
from core.i18n import translator
from app.config import ConfigManager   # per leggere la configurazione

def info():
    """Manifest del plugin."""
    return {
        "tag": "SYSTEM",
        "desc": translator.t("plugin_system_desc"),
        "comandi": {
            "help": translator.t("plugin_system_help_desc"),
            "reboot": translator.t("plugin_system_riavvia_desc"),
            "cmd:instruction": translator.t("plugin_system_cmd_desc"),
            "terminal": translator.t("plugin_system_terminale_desc"),
            "read log": translator.t("plugin_system_leggi_log_desc"),
            "errors": translator.t("plugin_system_errori_desc"),
            "time": translator.t("plugin_system_ora_desc"),
            "open:program": translator.t("plugin_system_apri_desc"),
            "explore:path": translator.t("plugin_system_esplora_desc"),
            "config:set:section,key,value": translator.t("plugin_system_config_set_desc")
        },
        "esempio": "[SYSTEM: read log] or [SYSTEM: terminal] or [SYSTEM: time]"
    }

def status():
    return translator.t("plugin_sistema_status_online")

def config_schema():
    """
    Schema di configurazione per il plugin Sistema.
    Permette di personalizzare programmi, cartelle e whitelist dei comandi shell.
    """
    return {
        "programs": {
            "type": "dict",
            "default": {
                "notepad": "notepad.exe",
                "chrome": "chrome.exe",
                "visual studio": r"C:\Program Files\Microsoft VS Code\Code.exe",
                "sillytavern": r"C:\SillyTavern\SillyTavern\Start.bat"
            },
            "description": translator.t("plugin_sistema_programs_desc")
        },
        "explorer_mappings": {
            "type": "dict",
            "default": {
                "desktop": os.path.expanduser("~\\Desktop"),
                "download": os.path.expanduser("~\\Downloads"),
                "documenti": os.path.expanduser("~\\Documents"),
                "core": os.path.join(os.getcwd(), "core"),
                "plugins": os.path.join(os.getcwd(), "plugins"),
                "memory": os.path.join(os.getcwd(), "memory"),
                "personality": os.path.join(os.getcwd(), "personality"),
                "logs": os.path.join(os.getcwd(), "logs")
            },
            "description": translator.t("plugin_sistema_explorer_mappings_desc")
        },
        "shell_command_whitelist": {
            "type": "list",
            "default": [],   # lista vuota = nessuna whitelist, tutti i comandi permessi
            "description": translator.t("plugin_sistema_shell_whitelist_desc")
        },
        "enable_config_set": {
            "type": "bool",
            "default": True,
            "description": translator.t("plugin_sistema_enable_config_set_desc")
        },
        "shell_command_timeout": {
            "type": "int",
            "default": 15,
            "min": 1,
            "max": 60,
            "description": translator.t("plugin_sistema_shell_timeout_desc")
        }
    }

def _get_programs():
    """Restituisce la mappa programmi dalla configurazione."""
    cfg = ConfigManager()
    return cfg.get_plugin_config("SYSTEM", "programs", {})

def _get_explorer_mappings():
    """Restituisce la mappa percorsi per esplora: dalla configurazione."""
    cfg = ConfigManager()
    return cfg.get_plugin_config("SYSTEM", "explorer_mappings", {})

def _get_shell_whitelist():
    """Restituisce la lista di comandi shell consentiti (regex)."""
    cfg = ConfigManager()
    return cfg.get_plugin_config("SYSTEM", "shell_command_whitelist", [])

def _is_shell_command_allowed(cmd):
    """Controlla se un comando shell è nella whitelist."""
    whitelist = _get_shell_whitelist()
    if not whitelist:
        return True   # whitelist vuota = tutto permesso
    for pattern in whitelist:
        if re.search(pattern, cmd, re.IGNORECASE):
            return True
    return False

def esegui(comando):
    """Esegue comandi shell o gestisce il ciclo vitale di Zentra."""
    logger.debug("PLUGIN_SYSTEM", f"execute() called with command: '{comando}'")
    
    cmd_originale = comando.strip()
    cmd = cmd_originale.lower()

    # --- 0. ORA ---
    if cmd == "ora" or cmd == "time":
        logger.debug("PLUGIN_SYSTEM", "Executing 'time' command")
        ora = datetime.datetime.now().strftime("%H:%M")
        return translator.t("plugin_system_time_is", time=ora)

    # --- 1. PROTOCOLLO RIAVVIO ---
    if any(x in cmd for x in ["riavvia", "reboot", "restart"]):
        logger.info(translator.t("plugin_system_reboot_admin"))
        logger.debug("PLUGIN_SYSTEM", "Executing reboot")
        print(f"\n\033[91m[SYSTEM] {translator.t('rebooting_msg')}\033[0m")
        sys.stdout.flush() 
        winsound.Beep(600, 150)
        winsound.Beep(400, 150)
        os._exit(0)
        return translator.t("rebooting_msg")

    # --- 2. LETTURA LOG E ERRORI ---
    if "log" in cmd or "errori" in cmd or "registro" in cmd or "errors" in cmd:
        solo_err = any(x in cmd for x in ["errori", "crash", "errors"])
        tipo_str = translator.t("plugin_system_log_errors") if solo_err else translator.t("plugin_system_log_events")
        logger.info(translator.t("plugin_system_log_access_msg", type=tipo_str))
        logger.debug("PLUGIN_SYSTEM", f"Reading logs, errors only: {solo_err}")
        
        risultato_log = logger.leggi_log(n=8, solo_errori=solo_err)
        return translator.t("plugin_system_log_analysis_done", type=tipo_str, log=risultato_log)

    # --- 3. APERTURA TERMINALE ESTERNO ---
    trigger_terminale = ["terminale", "console", "prompt", "apri cmd", "cmd", "terminal"]
    if cmd == "cmd" or any(x in cmd for x in trigger_terminale):
        try:
            logger.info("Opening independent external CMD instance.")
            logger.debug("PLUGIN_SYSTEM", "Opening terminal")
            subprocess.Popen("start cmd.exe", shell=True)
            return translator.t("plugin_system_terminal_opened")
        except Exception as e:
            logger.errore(f"Terminal open failed: {e}")
            logger.debug("PLUGIN_SYSTEM", f"Terminal open error: {e}")
            return translator.t("plugin_system_terminal_fail", error=str(e))
        
    # --- 4. APRI PROGRAMMA ---
    if cmd.startswith("apri:") or cmd.startswith("open:"):
        p_offset = 5 if cmd.startswith("apri:") else 5
        prog = cmd_originale[p_offset:].strip().lower()
        logger.debug("PLUGIN_SYSTEM", f"Opening program: {prog}")
        
        programs = _get_programs()
        if prog in programs:
            try:
                os.startfile(programs[prog])
                logger.debug("PLUGIN_SYSTEM", f"Program {prog} started")
                return translator.t("plugin_system_program_starting", prog=prog)
            except Exception as e:
                logger.debug("PLUGIN_SYSTEM", f"Error opening {prog}: {e}")
                return translator.t("plugin_system_program_error", prog=prog, error=str(e))
        else:
            # Se non è nella lista, prova a interpretarlo come comando diretto
            try:
                os.startfile(prog + ".exe")
                logger.debug("PLUGIN_SYSTEM", f"Direct open attempt: {prog}.exe")
                return translator.t("plugin_system_program_starting", prog=prog)
            except:
                logger.debug("PLUGIN_SYSTEM", f"Program {prog} unrecognized")
                return translator.t("plugin_system_program_unknown", prog=prog)

    # --- 5. ESPLORA CARTELLA ---
    if cmd.startswith("esplora:") or cmd.startswith("explore:"):
        e_offset = 8 if cmd.startswith("esplora:") else 8
        percorso = cmd_originale[e_offset:].strip().lower()
        logger.debug("PLUGIN_SYSTEM", f"Opening folder: {percorso}")
        
        mappings = _get_explorer_mappings()
        path = mappings.get(percorso, percorso)
        if os.path.exists(path):
            os.startfile(path)
            logger.debug("PLUGIN_SYSTEM", f"Folder {percorso} opened")
            return translator.t("plugin_system_folder_opened", folder=percorso)
        else:
            logger.debug("PLUGIN_SYSTEM", f"Path {percorso} not found")
            return translator.t("plugin_system_path_not_found", path=percorso)

    # --- 6. CONFIG: SET (solo se abilitato) ---
    if cmd.startswith("config:set:"):
        cfg = ConfigManager()
        if not cfg.get_plugin_config("SYSTEM", "enable_config_set", True):
            logger.debug("PLUGIN_SYSTEM", "config:set command disabled by configuration")
            return translator.t("plugin_system_config_disabled")
        args = cmd_originale[11:].strip().split(',')
        if len(args) == 3:
            sezione, chiave, valore = [x.strip() for x in args]
            logger.debug("PLUGIN_SYSTEM", f"Config modification: {sezione}.{chiave} = {valore}")
            try:
                with open('config.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if sezione in data and chiave in data[sezione]:
                    vecchio = data[sezione][chiave]
                    if isinstance(vecchio, bool):
                        valore = valore.lower() in ('true', '1', 'yes')
                    elif isinstance(vecchio, int):
                        valore = int(valore)
                    elif isinstance(vecchio, float):
                        valore = float(valore)
                    data[sezione][chiave] = valore
                    with open('config.json', 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=4)
                    logger.debug("PLUGIN_SYSTEM", "Config updated")
                    return translator.t("plugin_system_config_updated", section=sezione, key=chiave, value=str(valore))
                else:
                    logger.debug("PLUGIN_SYSTEM", f"Section or key not found")
                    return translator.t("plugin_system_config_not_found")
            except Exception as e:
                logger.debug("PLUGIN_SYSTEM", f"Config update error: {e}")
                return f"Error: {e}"
        else:
            return "Syntax: config:set:section,key,value"

    # --- 7. ESECUZIONE COMANDI SHELL (cmd:) ---
    if cmd.startswith("cmd:"):
        shell_cmd = cmd_originale[4:].strip()
        logger.debug("PLUGIN_SYSTEM", f"Comando shell: {shell_cmd}")
    else:
        shell_cmd = re.sub(r"^(comando_reale|sistema|cmd|esegui|shell)[:\s]+", "", cmd_originale, flags=re.IGNORECASE).strip()
        logger.debug("PLUGIN_SYSTEM", f"Comando shell (pulito): {shell_cmd}")

    if not shell_cmd or shell_cmd.lower() == "help":
        logger.debug("PLUGIN_SYSTEM", "Nessun comando valido, restituisco help")
        return translator.t("plugin_sistema_help_error")

    # Controlla whitelist
    if not _is_shell_command_allowed(shell_cmd):
        logger.debug("PLUGIN_SYSTEM", f"Command not authorized by whitelist: {shell_cmd}")
        return translator.t("plugin_system_shell_unauthorized")

    timeout = ConfigManager().get_plugin_config("SYSTEM", "shell_command_timeout", 15)

    try:
        logger.info(f"Executing shell command: {shell_cmd}")
        logger.debug("PLUGIN_SYSTEM", f"Executing subprocess: {shell_cmd}")
        output = subprocess.check_output(shell_cmd, shell=True, text=True, stderr=subprocess.STDOUT, timeout=timeout)
        logger.debug("PLUGIN_SYSTEM", f"Output received: {len(output)} characters")
        return output if output.strip() else translator.t("plugin_system_shell_success", cmd=shell_cmd)
    except subprocess.CalledProcessError as e:
        msg_err = f"Shell Error: {e.output}"
        logger.errore(msg_err)
        logger.debug("PLUGIN_SYSTEM", f"Subprocess error: {e}")
        return msg_err
    except Exception as e:
        logger.errore(f"Unexpected shell error: {e}")
        logger.debug("PLUGIN_SYSTEM", f"Exception: {e}")
        return f"Error: {str(e)}"
        return f"Errore: {str(e)}"