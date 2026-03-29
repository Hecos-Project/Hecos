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
        """Carica le impostazioni da config.json con migrazione automatica all'inglese."""
        try:
            import os
            if not os.path.exists(self.config_path):
                return self._get_defaults()
                
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Migrazione automatica se rilevate chiavi italiane
            if "ia" in data or "ascolto" in data or "lingua" in data:
                data = self._migrate_to_english(data)
                # Salviamo subito la versione migrata
                self.config = data
                self.save()
                
            # --- Volatility cleanup on load ---
            # If persistence is DISABLED, we clear the memory on load so they don't survive a reboot.
            if not data.get("ai", {}).get("save_special_instructions", False):
                if "ai" in data:
                    data["ai"]["special_instructions"] = ""

            return data
        except Exception as e:
            logger.error(f"[CONFIG] Critical configuration loading error: {e}")
            return self._get_defaults()

    def _get_defaults(self):
        return {
            "backend": {"type": "ollama", "ollama": {}}, 
            "ai": {"special_instructions": "", "save_special_instructions": False},
            "language": "en",
            "routing_engine": {"mode": "auto", "legacy_models": ""},
            "listening": {
                "energy_threshold": 450,
                "silence_timeout": 5,
                "phrase_limit": 15,
                "push_to_talk": False,
                "ptt_hotkey": "ctrl+shift"
            }
        }

    def _migrate_to_english(self, data):
        """Maps legacy Italian keys to the new English standard."""
        # Top-level mapping
        top_mapping = {
            "ia": "ai",
            "ascolto": "listening",
            "filtri": "filters",
            "voce": "voice",
            "lingua": "language",
            "motore_routing": "routing_engine"
        }
        
        new_data = {}
        for k, v in data.items():
            new_key = top_mapping.get(k, k)
            
            # Recursive handling for known sub-sections
            if new_key == "ai" and isinstance(v, dict):
                v = {
                    "active_personality": v.get("personalita_attiva", v.get("active_personality", "")),
                    "available_personalities": v.get("personalita_disponibili", v.get("available_personalities", {})),
                    "special_instructions": v.get("istruzioni_speciali", v.get("special_instructions", "")),
                    "save_special_instructions": v.get("salva_istruzioni_speciali", v.get("save_special_instructions", False))
                }
            elif new_key == "bridge" and isinstance(v, dict):
                v = {
                    "use_processor": v.get("usa_processore", v.get("use_processor", False)),
                    "chunk_delay_ms": v.get("ritardo_chunk_ms", v.get("chunk_delay_ms", 0)),
                    "debug_log": v.get("debug_log", True),
                    "remove_think_tags": v.get("rimuovi_think_tags", v.get("remove_think_tags", True)),
                    "local_voice_enabled": v.get("voce_locale_abilitata", v.get("local_voice_enabled", False)),
                    "enable_tools": v.get("abilita_tools", v.get("enable_tools", True))
                }
            elif new_key == "filters" and isinstance(v, dict):
                v = {
                    "remove_asterisks": v.get("rimuovi_asterischi", v.get("remove_asterisks", True)),
                    "remove_round_brackets": v.get("rimuovi_parentesi_tonde", v.get("remove_round_brackets", True)),
                    "remove_square_brackets": v.get("rimuovi_parentesi_quadre", v.get("remove_square_brackets", False)),
                    "custom_replacements": v.get("sostituzioni_personalizzate", v.get("custom_replacements", {}))
                }
            elif new_key == "voice" and isinstance(v, dict):
                # Keep original values but ensure key is renamed if it was 'voce'
                pass
            elif new_key == "routing_engine" and isinstance(v, dict):
                v = {
                    "mode": v.get("modalita", v.get("mode", "auto")),
                    "legacy_models": v.get("modelli_legacy", v.get("legacy_models", ""))
                }
            
            new_data[new_key] = v
        
        logger.info("[CONFIG] Global migration to English completed.")
        return new_data

    def save(self):
        """Salva la configurazione corrente e aggiorna componenti se necessario."""
        import os
        try:
            # Ricarichiamo il file per vedere la lingua precedente (se esiste)
            old_lang = None
            if os.path.exists(self.config_path):
                try:
                    with open(self.config_path, 'r', encoding='utf-8') as f:
                        old_data = json.load(f)
                        old_lang = old_data.get("language") or old_data.get("lingua")
                except: pass

            # Flag per il monitor.py (evita riavvii inutili se config salvato da app)
            try:
                with open(".config_saved_by_app", "w") as flag_file:
                    flag_file.write("1")
            except: pass
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            
            # Notifica traduttore se la lingua è cambiata
            new_lang = self.config.get("language")
            if new_lang and new_lang != old_lang:
                from core.i18n import translator
                translator.get_translator().set_language(new_lang)
                logger.info("CONFIG", f"Language updated to: {new_lang}")

            logger.info("[CONFIG] Configuration saved successfully.")
            return True
        except Exception as e:
            logger.error(f"[CONFIG] Save error: {e}")
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

    def update_config(self, new_data):
        """Deep merge new_data into current config and save."""
        self.reload() # Ensure we have latest from disk
        self._deep_update(self.config, new_data)
        return self.save()

    def _deep_update(self, base, patch):
        for k, v in patch.items():
            if isinstance(v, dict) and k in base and isinstance(base[k], dict):
                self._deep_update(base[k], v)
            else:
                base[k] = v

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