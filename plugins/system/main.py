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
        def error(self, *args, **kwargs): print("[SYS_ERR]", *args)
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
    Central system tools. Allows managing the OS, reading the time,
    executing terminal commands, managing programs, folders, and configurations.
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
        Returns the current local time (HH:MM).
        Use this tool to answer when asked for the exact time.
        """
        ora = datetime.datetime.now().strftime("%H:%M")
        logger.debug(f"PLUGIN_{self.tag}", "Executing 'time' command")
        return translator.t("plugin_system_time_is", time=ora)

    def reboot_system(self) -> str:
        """
        Reboots the entire Zentra Core system.
        Use this tool if there are critical issues or if the user requests a reboot.
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
        
        risultato_log = logger.read_logs(n=8, errors_only=False)
        return translator.t("plugin_system_log_analysis_done", type=tipo_str, log=risultato_log)

    def read_errors(self) -> str:
        """
        Reads specifically the latest errors (crashes, exceptions) recorded by the system.
        Essential for diagnosing malfunctions.
        """
        tipo_str = translator.t("plugin_system_log_errors")
        logger.info(translator.t("plugin_system_log_access_msg", type=tipo_str))
        logger.debug(f"PLUGIN_{self.tag}", "Reading error logs")
        
        risultato_log = logger.read_logs(n=8, errors_only=True)
        return translator.t("plugin_system_log_analysis_done", type=tipo_str, log=risultato_log)

    def read_debug_logs(self) -> str:
        """
        Reads the technical debug logs (LiteLLM, Brain processing).
        Useful for advanced developers and deep diagnostics.
        """
        tipo_str = "DEBUG"
        logger.info(translator.t("plugin_system_log_access_msg", type=tipo_str))
        logger.debug(f"PLUGIN_{self.tag}", "Reading debug logs")
        
        risultato_log = logger.read_logs(n=10, debug_only=True)
        return translator.t("plugin_system_log_analysis_done", type=tipo_str, log=risultato_log)

    def open_terminal(self) -> str:
        """
        Opens a new independent Windows command prompt (CMD) window.
        """
        try:
            logger.info("Opening independent external CMD instance.")
            subprocess.Popen("start cmd.exe", shell=True)
            return translator.t("plugin_system_terminal_opened")
        except Exception as e:
            logger.error(f"Terminal open failed: {e}")
            return translator.t("plugin_system_terminal_fail", error=str(e))

    def open_program(self, program_name: str) -> str:
        """
        Starts a local program specified by name.
        
        :param program_name: The name of the program to open (e.g., 'notepad', 'chrome').
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
        OPENS a graphical Windows Explorer window for the specified folder. 
        Use this tool when the user wants to visually 'see', 'open', or 'explore' a directory on their desktop.
        
        :param folder_path: The path or alias of the folder (e.g., 'desktop', 'download', 'documents').
        """
        percorso = folder_path.strip().lower()
        logger.debug(f"PLUGIN_{self.tag}", f"Opening folder: {percorso}")
        
        mappings = self._get_explorer_mappings()
        
        # Alias resolution for common folders
        if percorso not in mappings:
            if percorso == "downloads" and "download" in mappings:
                path = mappings["download"]
            elif percorso == "download" and "downloads" in mappings:
                path = mappings["downloads"]
            elif percorso == "documents" and "documenti" in mappings:
                path = mappings["documenti"]
            elif percorso == "documenti" and "documents" in mappings:
                path = mappings["documents"]
            else:
                path = percorso
        else:
            path = mappings[percorso]

        # Expand user path fallback just in case
        if not os.path.exists(path):
            expanded_path = os.path.expanduser(f"~\\{percorso.capitalize()}")
            if os.path.exists(expanded_path):
                path = expanded_path

        if os.path.exists(path):
            os.startfile(path)
            return translator.t("plugin_system_folder_opened", folder=percorso)
        else:
            return translator.t("plugin_system_path_not_found", path=percorso)

    def set_configuration(self, section: str, key: str, value: str) -> str:
        """
        Modifies a value within the main configuration file (config.json).
        Warning: use only upon explicit user request.
        
        :param section: The root section of the config (e.g., 'llm', 'backend', 'voice').
        :param key: The specific key to modify.
        :param value: The new value (text, numeric, or 'true'/'false').
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
        Executes a shell command (cmd.exe) in the background and returns the output.
        Ideal for diagnostics, automation, or system queries.
        
        :param command: The exact command to pass to the shell.
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
            logger.error(msg_err)
            return msg_err
        except Exception as e:
            logger.error(f"Unexpected shell error: {e}")
            return f"Error: {e}"

# Istanzia pubblicamente lo strumento per l'esportazione verso il Core
tools = SystemTools()

# --- COMPATIBILITY SHIMS ---
def info():
    return {"tag": tools.tag, "desc": tools.desc}

def status():
    return tools.status

def execute(comando: str) -> str:
    """Compatibilità legacy: smista i comandi testuali ai nuovi metodi ad oggetti."""
    c = comando.strip()
    c_lower = c.lower()
    
    if c_lower in ("terminal", "cmd", "terminale", "prompt", "open_terminal"):
        return tools.open_terminal()
    elif c_lower.startswith("open:") or c_lower.startswith("program:") or c_lower.startswith("open_program:"):
        prog = c.split(":", 1)[1].strip()
        return tools.open_program(prog)
    elif c_lower.startswith("explore:") or c_lower.startswith("folder:") or c_lower.startswith("apri:") or c_lower.startswith("explore_folder:"):
        folder = c.split(":", 1)[1].strip()
        return tools.explore_folder(folder)
    elif c_lower in ("reboot", "reboot_system"):
        return tools.reboot_system()
    elif c_lower in ("logs", "log", "read_logs"):
        return tools.read_logs()
    elif c_lower in ("errors", "errori", "read_errors"):
        return tools.read_errors()
    elif c_lower in ("debug", "debug_logs", "read_debug_logs"):
        return tools.read_debug_logs()
    elif c_lower in ("time", "ora", "tempo", "get_time"):
        return tools.get_time()
    
    if c_lower.startswith("shell:") or c_lower.startswith("execute_shell_command:"):
        shell_cmd = c.split(":", 1)[1].strip()
        return tools.execute_shell_command(shell_cmd)
        
    return f"Errore: Comando legacy '{comando}' non supportato o mancante. Usa Tools Calling."