"""Modulo principale del plugin System."""
import sys
import subprocess
import os
import winsound
import time
import re
import datetime
import json
try:
    from core.logging import logger
    from core.i18n import translator
    from app.config import ConfigManager
except ImportError:
    class DummyLogger:
        def debug(self, *args, **kwargs): print("[SYS_DEBUG]", *args)
        def info(self, *args, **kwargs): print("[SYS_INFO]", *args)
        def errore(self, *args, **kwargs): print("[SYS_ERR]", *args)
    logger = DummyLogger()
    class DummyTranslator:
        def t(self, key, **kwargs): return key
    translator = DummyTranslator()
    class DummyConfigMgr:
        def __init__(self): self.config = {}
        def get_plugin_config(self, tag, key, default): return default
    ConfigManager = DummyConfigMgr

class SystemTools:
    """
    Plugin: System
    Strumenti centrali di sistema. Permette di gestire il SO, leggere l'ora, 
    eseguire comandi terminale, gestire programmi, cartelle e configurazioni.
    """

    def __init__(self):
        self.tag = "SYSTEM"
        self.desc = translator.t("plugin_system_desc")
        self.status = translator.t("plugin_sistema_status_online")
        
        self.config_schema = {
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
                "default": [],
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

    # --- METODI PRIVATI (HELPER) ---

    def _get_programs(self):
        cfg = ConfigManager()
        return cfg.get_plugin_config(self.tag, "programs", {})

    def _get_explorer_mappings(self):
        cfg = ConfigManager()
        return cfg.get_plugin_config(self.tag, "explorer_mappings", {})

    def _is_shell_command_allowed(self, cmd: str) -> bool:
        cfg = ConfigManager()
        whitelist = cfg.get_plugin_config(self.tag, "shell_command_whitelist", [])
        if not whitelist:
            return True # vuota = tutto permesso
        for pattern in whitelist:
            if re.search(pattern, cmd, re.IGNORECASE):
                return True
        return False

    # --- METODI PUBBLICI (FUNCTION CALLING TOOLS) ---

    def get_time(self) -> str:
        """
        Restituisce l'ora locale attuale formattata (HH:MM).
        Usa questo strumento per rispondere quando ti viene chiesta l'ora esatta.
        """
        ora = datetime.datetime.now().strftime("%H:%M")
        logger.debug(f"PLUGIN_{self.tag}", "Executing 'time' command")
        return translator.t("plugin_system_time_is", time=ora)

    def reboot_system(self) -> str:
        """
        Riavvia l'intero sistema Zentra Core.
        Usa questo strumento se ci sono problemi critici o se l'utente richiede un riavvio.
        """
        logger.info(translator.t("plugin_system_reboot_admin"))
        logger.debug(f"PLUGIN_{self.tag}", "Executing reboot")
        print(f"\n\033[91m[{self.tag}] {translator.t('rebooting_msg')}\033[0m")
        sys.stdout.flush() 
        winsound.Beep(600, 150)
        winsound.Beep(400, 150)
        os._exit(0)
        return translator.t("rebooting_msg")

    def read_logs(self) -> str:
        """
        Legge gli ultimi eventi registrati nei file di log generali del sistema.
        Utile per il debug e per capire cosa è successo di recente.
        """
        tipo_str = translator.t("plugin_system_log_events")
        logger.info(translator.t("plugin_system_log_access_msg", type=tipo_str))
        logger.debug(f"PLUGIN_{self.tag}", "Reading standard logs")
        
        risultato_log = logger.leggi_log(n=8, solo_errori=False)
        return translator.t("plugin_system_log_analysis_done", type=tipo_str, log=risultato_log)

    def read_errors(self) -> str:
        """
        Legge specificamente gli ultimi errori (crash, eccezioni) registrati dal sistema nel log degli errori.
        Essenziale per diagnosticare malfunzionamenti.
        """
        tipo_str = translator.t("plugin_system_log_errors")
        logger.info(translator.t("plugin_system_log_access_msg", type=tipo_str))
        logger.debug(f"PLUGIN_{self.tag}", "Reading error logs")
        
        risultato_log = logger.leggi_log(n=8, solo_errori=True)
        return translator.t("plugin_system_log_analysis_done", type=tipo_str, log=risultato_log)

    def open_terminal(self) -> str:
        """
        Apre una nuova finestra indipendente del prompt dei comandi di Windows (CMD).
        """
        try:
            logger.info("Opening independent external CMD instance.")
            subprocess.Popen("start cmd.exe", shell=True)
            return translator.t("plugin_system_terminal_opened")
        except Exception as e:
            logger.errore(f"Terminal open failed: {e}")
            return translator.t("plugin_system_terminal_fail", error=str(e))

    def open_program(self, program_name: str) -> str:
        """
        Avvia un programma locale specificato dal nome.
        
        :param program_name: Il nome del programma da aprire (es. 'notepad', 'chrome', o altri nomi registrati).
        """
        prog = program_name.strip().lower()
        logger.debug(f"PLUGIN_{self.tag}", f"Opening program: {prog}")
        
        programs = self._get_programs()
        if prog in programs:
            try:
                os.startfile(programs[prog])
                return translator.t("plugin_system_program_starting", prog=prog)
            except Exception as e:
                return translator.t("plugin_system_program_error", prog=prog, error=str(e))
        else:
            try:
                os.startfile(prog + ".exe")
                return translator.t("plugin_system_program_starting", prog=prog)
            except:
                return translator.t("plugin_system_program_unknown", prog=prog)

    def explore_folder(self, folder_path: str) -> str:
        """
        Apre il file manager del sistema operativo in una cartella specifica.
        
        :param folder_path: Il percorso o l'alias della cartella (es. 'desktop', 'download', o un path assoluto).
        """
        percorso = folder_path.strip().lower()
        logger.debug(f"PLUGIN_{self.tag}", f"Opening folder: {percorso}")
        
        mappings = self._get_explorer_mappings()
        path = mappings.get(percorso, percorso)
        if os.path.exists(path):
            os.startfile(path)
            return translator.t("plugin_system_folder_opened", folder=percorso)
        else:
            return translator.t("plugin_system_path_not_found", path=percorso)

    def set_configuration(self, section: str, key: str, value: str) -> str:
        """
        Modifica un valore all'interno del file di configurazione principale (config.json).
        Attenzione: va usato solo su richiesta esplicita dell'utente.
        
        :param section: La sezione root del config (es. 'llm', 'backend', 'voce').
        :param key: La chiave specifica da modificare.
        :param value: Il nuovo valore (testo, numerico o 'true'/'false').
        """
        cfg = ConfigManager()
        if not cfg.get_plugin_config(self.tag, "enable_config_set", True):
            return translator.t("plugin_system_config_disabled")
            
        logger.debug(f"PLUGIN_{self.tag}", f"Config modification: {section}.{key} = {value}")
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
            if section in data and key in data[section]:
                vecchio = data[section][key]
                val_inserito = value.strip()
                if isinstance(vecchio, bool):
                    val_inserito = val_inserito.lower() in ('true', '1', 'yes')
                elif isinstance(vecchio, int):
                    val_inserito = int(val_inserito)
                elif isinstance(vecchio, float):
                    val_inserito = float(val_inserito)
                
                data[section][key] = val_inserito
                with open('config.json', 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4)
                return translator.t("plugin_system_config_updated", section=section, key=key, value=str(val_inserito))
            else:
                return translator.t("plugin_system_config_not_found")
        except Exception as e:
            return f"Error: {e}"

    def execute_shell_command(self, command: str) -> str:
        """
        Esegue un comando shell (cmd.exe) nel terminale in background e restituisce l'output.
        Ideale per diagnostica, automazione o interrogazioni di sistema.
        
        :param command: Il comando esatto da passare alla shell.
        """
        shell_cmd = command.strip()
        logger.debug(f"PLUGIN_{self.tag}", f"Executing shell command: {shell_cmd}")

        if not shell_cmd:
            return translator.t("plugin_sistema_help_error")

        if not self._is_shell_command_allowed(shell_cmd):
            return translator.t("plugin_system_shell_unauthorized")

        timeout = ConfigManager().get_plugin_config(self.tag, "shell_command_timeout", 15)

        try:
            output = subprocess.check_output(shell_cmd, shell=True, text=True, stderr=subprocess.STDOUT, timeout=timeout)
            return output if output.strip() else translator.t("plugin_system_shell_success", cmd=shell_cmd)
        except subprocess.CalledProcessError as e:
            msg_err = f"Shell Error: {e.output}"
            logger.errore(msg_err)
            return msg_err
        except Exception as e:
            logger.errore(f"Unexpected shell error: {e}")
            return f"Error: {e}"

# Istanzia pubblicamente lo strumento per l'esportazione verso il Core
tools = SystemTools()

# --- COMPATIBILITY SHIMS ---
def info():
    return {"tag": tools.tag, "desc": tools.desc}

def status():
    return tools.status

def esegui(comando):
    # Fallback legacy (molto limitato)
    return f"Use tool calling for {comando}"