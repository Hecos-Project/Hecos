import sys
import subprocess
import os
import winsound
import time
import re
import datetime
import json
from plugins_legacy.base import BaseLegacyPlugin

try:
    from core.logging import logger
    from core.i18n import translator
    from app.config import ConfigManager
except ImportError:
    pass

class SystemLegacyPlugin(BaseLegacyPlugin):
    """
    Legacy Object-Oriented version of the SYSTEM plugin.
    Instead of exporting complex JSON dictionaries, it receives parsed strings from the Processor (e.g.: 'open:calc')
    and executes the corresponding Python logic.
    """
    def __init__(self):
        desc = translator.t("plugin_system_desc") if 'translator' in globals() else "System tools"
        super().__init__("SYSTEM", desc)
        
    def get_commands(self) -> dict:
        return {
            "time": "Returns the current local time",
            "reboot": "Reboots the Zentra Core system",
            "terminal": "Opens a new system command prompt",
            "open:<name>": "Starts a local program by name",
            "explore:<folder>": "Opens folders like desktop or downloads",
            "shell:<command>": "Executes shell commands and reads output"
        }
        
    # --- HELPERS ---
    def _get_programs(self):
        if 'ConfigManager' in globals():
            cfg = ConfigManager()
            return cfg.get_plugin_config(self.tag, "programs", {})
        return {}
        
    def _get_explorer_mappings(self):
        if 'ConfigManager' in globals():
            cfg = ConfigManager()
            return cfg.get_plugin_config(self.tag, "explorer_mappings", {})
        return {}

    # --- CORE LOGIC ---
    def process_tag(self, command: str) -> str:
        command = command.strip()
        if 'logger' in globals():
            logger.debug("PLUGIN_SYSTEM_LEGACY", f"Received command: {command}")
        
        if command == "time":
            ora = datetime.datetime.now().strftime("%H:%M")
            return translator.t("plugin_system_time_is", time=ora) if 'translator' in globals() else f"Time is {ora}"
            
        elif command == "reboot" or command == "riavvia":
            print(f"\n\033[91m[{self.tag}] Forced Reboot...\033[0m")
            sys.stdout.flush() 
            winsound.Beep(600, 150)
            winsound.Beep(400, 150)
            os._exit(0)
            return "Rebooting..."
            
        elif command == "terminal" or command == "terminale":
            try:
                subprocess.Popen("start cmd.exe", shell=True)
                return translator.t("plugin_system_terminal_opened") if 'translator' in globals() else "Terminal opened."
            except Exception as e:
                return f"Error: {e}"
                
        elif command.startswith("open:") or command.startswith("apri:"):
            prefix = "open:" if command.startswith("open:") else "apri:"
            prog = command[len(prefix):].strip().lower()
            programs = self._get_programs()
            if prog in programs:
                try:
                    os.startfile(programs[prog])
                    return f"Program {prog} starting."
                except Exception as e:
                    return f"Error: {e}"
            else:
                try:
                    os.startfile(prog + ".exe")
                    return f"Program {prog}.exe starting."
                except Exception:
                    return f"Unknown or not found program: {prog}"
                    
        elif command.startswith("explore:") or command.startswith("esplora:"):
            prefix = "explore:" if command.startswith("explore:") else "esplora:"
            cartella = command[len(prefix):].strip().lower()
            mappings = self._get_explorer_mappings()
            path = mappings.get(cartella, cartella)
            if os.path.exists(path):
                os.startfile(path)
                return f"Folder {cartella} opened on Windows."
            else:
                return f"Unknown folder path: {cartella}"
                
        elif command.startswith("shell:") or command.startswith("cmd:"):
            prefix = "shell:" if command.startswith("shell:") else "cmd:"
            shell_cmd = command[len(prefix):].strip()
            if not shell_cmd: return "No command provided."
            try:
                output = subprocess.check_output(shell_cmd, shell=True, text=True, stderr=subprocess.STDOUT, timeout=10)
                return output if output.strip() else f"Command executed: {shell_cmd}"
            except subprocess.CalledProcessError as e:
                return f"Shell Error: {e.output}"
            except Exception as e:
                return f"Unexpected shell error: {e}"
                
        return f"Invalid tag syntax for: {command}"

def get_plugin():
    return SystemLegacyPlugin()
