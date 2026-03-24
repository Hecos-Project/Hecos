"""
Gestione centralizzata della configurazione.
"""

import json
import time
from core.logging import logger

class ConfigManager:
    def __init__(self, config_path="config.json"):
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self):
        """Carica le impostazioni da config.json."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.errore(f"[CONFIG] Critical configuration loading error: {e}")
            return {"backend": {"tipo": "ollama", "ollama": {}}, "ia": {}}

    def save(self):
        """Salva la configurazione corrente e aggiorna componenti se necessario."""
        import os
        try:
            # Ricarichiamo il file per vedere la lingua precedente (se esiste)
            lingua_precedente = None
            if os.path.exists(self.config_path):
                try:
                    with open(self.config_path, 'r', encoding='utf-8') as f:
                        old_data = json.load(f)
                        lingua_precedente = old_data.get("lingua")
                except: pass

            # Flag per il monitor.py (evita riavvii inutili se config salvato da app)
            try:
                with open(".config_saved_by_app", "w") as flag_file:
                    flag_file.write("1")
            except: pass
                
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            
            # Notifica traduttore se la lingua è cambiata
            nuova_lingua = self.config.get("lingua")
            if nuova_lingua and nuova_lingua != lingua_precedente:
                from core.i18n import translator
                translator.get_translator().set_language(nuova_lingua)
                logger.info("CONFIG", f"Language updated to: {nuova_lingua}")

            logger.info("[CONFIG] Configuration saved successfully.")
            return True
        except Exception as e:
            logger.errore(f"[CONFIG] Save error: {e}")
            return False

    def get(self, *keys, default=None):
        """Ottiene un valore annidato, es. config.get('backend', 'tipo')"""
        value = self.config
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
                if value is None:
                    return default
            else:
                return default
        return value

    def set(self, value, *keys):
        """Imposta un valore annidato, es. config.set('ollama', 'backend', 'tipo')"""
        if len(keys) == 0:
            return False
        target = self.config
        for key in keys[:-1]:
            if key not in target:
                target[key] = {}
            target = target[key]
        target[keys[-1]] = value
        return True

    def reload(self):
        """Ricarica la configurazione dal file."""
        self.config = self._load_config()
        return self.config

    def get_plugin_config(self, plugin_tag, key=None, default=None):
        """
        Restituisce la configurazione di un plugin.
        - Se key è None, restituisce l'intero dizionario del plugin.
        - Altrimenti restituisce il valore per quella chiave, o default se non esiste.
        """
        plugins = self.config.get("plugins", {})
        plugin_cfg = plugins.get(plugin_tag, {})
        if key is None:
            return plugin_cfg
        return plugin_cfg.get(key, default)

    def set_plugin_config(self, plugin_tag, key, value):
        """Imposta un valore di configurazione per un plugin e salva."""
        if "plugins" not in self.config:
            self.config["plugins"] = {}
        if plugin_tag not in self.config["plugins"]:
            self.config["plugins"][plugin_tag] = {}
        self.config["plugins"][plugin_tag][key] = value
        self.save()