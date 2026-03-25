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
    Versione Legacy a Oggetti del plugin SYSTEM.
    Invece di esportare dizionari JSON complessi, riceve le stringhe parseate dal Processore (es: 'apri:calc')
    ed esegue la logica Python corrispondente.
    """
    def __init__(self):
        desc = translator.t("plugin_system_desc") if 'translator' in globals() else "System tools"
        super().__init__("SYSTEM", desc)
        
    def ottieni_comandi(self) -> dict:
        return {
            "time": "Restituisce l'ora corrente",
            "riavvia": "Riavvia Zentra",
            "terminale": "Apre un prompt dei comandi",
            "apri:<nome>": "Apre un programma locale",
            "esplora:<cartella>": "Apre cartelle come desktop o download",
            "cmd:<comando>": "Esegue comandi shell e ne legge l'output"
        }
        
    # --- HELPER (Presi dal modulo Nativo) ---
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
    def elabora_tag(self, comando: str) -> str:
        comando = comando.strip()
        logger.debug("PLUGIN_SYSTEM_LEGACY", f"Ricevuto comando: {comando}")
        
        if comando == "time":
            ora = datetime.datetime.now().strftime("%H:%M")
            return translator.t("plugin_system_time_is", time=ora) if 'translator' in globals() else f"Time is {ora}"
            
        elif comando == "riavvia":
            print(f"\n\033[91m[{self.tag}] Riavvio forzato...\033[0m")
            sys.stdout.flush() 
            winsound.Beep(600, 150)
            winsound.Beep(400, 150)
            os._exit(0)
            return "Rebooting..."
            
        elif comando == "terminale":
            try:
                subprocess.Popen("start cmd.exe", shell=True)
                return translator.t("plugin_system_terminal_opened") if 'translator' in globals() else "Terminal opened."
            except Exception as e:
                return f"Error: {e}"
                
        elif comando.startswith("apri:"):
            prog = comando[5:].strip().lower()
            programs = self._get_programs()
            if prog in programs:
                try:
                    os.startfile(programs[prog])
                    return f"Programma {prog} in avvio."
                except Exception as e:
                    return f"Errore: {e}"
            else:
                try:
                    os.startfile(prog + ".exe")
                    return f"Programma {prog}.exe in avvio."
                except Exception:
                    return f"Programma sconosciuto o non trovato: {prog}"
                    
        elif comando.startswith("esplora:"):
            cartella = comando[8:].strip().lower()
            mappings = self._get_explorer_mappings()
            path = mappings.get(cartella, cartella)
            if os.path.exists(path):
                os.startfile(path)
                return f"Cartella {cartella} aperta su Windows."
            else:
                return f"Percorso cartella sconosciuto: {cartella}"
                
        elif comando.startswith("cmd:"):
            shell_cmd = comando[4:].strip()
            if not shell_cmd: return "Nessun comando fornito."
            try:
                # Breve timeout fisso per prevenire blocchi eterni del modello piccolo
                output = subprocess.check_output(shell_cmd, shell=True, text=True, stderr=subprocess.STDOUT, timeout=10)
                return output if output.strip() else f"Comando eseguito: {shell_cmd}"
            except subprocess.CalledProcessError as e:
                return f"Shell Error: {e.output}"
            except Exception as e:
                return f"Errore imprevisto shell: {e}"
                
        return f"Sintassi tag non valida per: {comando}"

def get_plugin():
    return SystemLegacyPlugin()
