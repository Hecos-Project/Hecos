"""
Gestione centralizzata della configurazione.
"""

import json
import time
from core import logger

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
            logger.errore(f"[CONFIG] Errore critico caricamento config: {e}")
            return {"backend": {"tipo": "ollama", "ollama": {}}, "ia": {}}

    def save(self):
        """Salva la configurazione corrente."""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            logger.info("[CONFIG] Configurazione salvata correttamente.")
            return True
        except Exception as e:
            logger.errore(f"[CONFIG] Errore salvataggio: {e}")
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