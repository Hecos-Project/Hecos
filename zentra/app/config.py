"""
MODULE: Config Manager
DESCRIPTION: Loads, validates and saves the main system configuration.
             Uses YAML + Pydantic v2. Auto-migrates from legacy JSON on first run.
"""

import os as _os
import json
import time
from zentra.core.logging import logger

# Lazy imports (avoid circular imports at module level)
def _get_yaml_utils():
    from zentra.config.yaml_utils import load_yaml, save_yaml
    return load_yaml, save_yaml

def _get_schema():
    from zentra.config.schemas.system_schema import SystemConfig
    return SystemConfig

# Project root and Zentra package root
_PROJECT_ROOT = _os.path.normpath(_os.path.join(_os.path.dirname(__file__), "..", ".."))
_ZENTRA_DIR = _os.path.join(_PROJECT_ROOT, "zentra")

_CONFIG_YAML_PATH = _os.path.join(_ZENTRA_DIR, "config", "data", "system.yaml")
_CONFIG_JSON_PATH = _os.path.join(_ZENTRA_DIR, "config", "data", "system.json")


class ConfigManager:
    def __init__(self, config_path=None):
        # config_path kept for backward compat — overrides YAML path if given
        if config_path is not None:
            # Legacy call with explicit path: try to honour it by deriving YAML path
            base = _os.path.splitext(config_path)[0]
            self._yaml_path = base + ".yaml"
            self._json_path = config_path
        else:
            self._yaml_path = _CONFIG_YAML_PATH
            self._json_path = _CONFIG_JSON_PATH

        self._ensure_files_exist()
        self._model = self._load_model()
        self.config = self._model.model_dump()  # plain dict kept for full backward compat

    def _ensure_files_exist(self):
        """Automatically setup initial config files from templates if missing."""
        import shutil
        data_dir = _os.path.dirname(self._yaml_path)
        
        # Files to check and auto-generate if missing
        files_to_check = [
            "system.yaml",
            "routing_overrides.yaml",
            "audio.yaml",
            "agent.yaml",
            "media.yaml",
            "keys.yaml"
        ]
        
        for filename in files_to_check:
            yaml_file = _os.path.join(data_dir, filename)
            example_file = yaml_file + ".example"
            
            if not _os.path.exists(yaml_file) and _os.path.exists(example_file):
                try:
                    shutil.copy2(example_file, yaml_file)
                    logger.info(f"[CONFIG] Auto-generated {filename} from template.")
                except Exception as e:
                    logger.error(f"[CONFIG] Failed to auto-generate {filename}: {e}")

        # Check for .env in zentra/ folder
        env_file = _os.path.join(_ZENTRA_DIR, ".env")
        env_example = env_file + ".example"
        if not _os.path.exists(env_file) and _os.path.exists(env_example):
            try:
                shutil.copy2(env_example, env_file)
                logger.info("[CONFIG] Auto-generated .env from template.")
            except Exception as e:
                logger.error(f"[CONFIG] Failed to auto-generate .env: {e}")


    # ──────────────────────────────────────────────────────────────────────────
    # INTERNAL
    # ──────────────────────────────────────────────────────────────────────────

    def _load_model(self):
        """Load and validate the YAML config (auto-migrating from JSON if needed)."""
        try:
            load_yaml, _ = _get_yaml_utils()
            SystemConfig = _get_schema()
            model = load_yaml(self._yaml_path, SystemConfig)
            self._apply_volatility(model)
            self._run_italian_migration(model)
            return model
        except Exception as e:
            logger.error(f"[CONFIG] Critical error loading config: {e}")
            SystemConfig = _get_schema()
            return SystemConfig()

    def _apply_volatility(self, model):
        """If save_special_instructions is False, clear special_instructions on load."""
        if not model.ai.save_special_instructions:
            model.ai.special_instructions = ""

    def _run_italian_migration(self, model):
        """
        No-op: Italian key migration was handled by the old JSON loader.
        The YAML auto-migration in yaml_utils already validated data through Pydantic,
        so any remaining Italian keys in the JSON would have been ignored (defaulted).
        This stub is kept for documentation purposes.
        """
        pass

    def _sync_dict(self):
        """Keep self.config dict in sync with the underlying Pydantic model."""
        self.config = self._model.model_dump()

    @property
    def yaml_path(self):
        return self._yaml_path

    # ──────────────────────────────────────────────────────────────────────────
    # PUBLIC API
    # ──────────────────────────────────────────────────────────────────────────

    def save(self):
        """Serialize the current config to YAML and persist it."""
        try:
            old_lang = self.config.get("language")

            # Flag for monitor.py to avoid unnecessary restarts
            try:
                flag_path = _os.path.join(_PROJECT_ROOT, ".config_saved_by_app")
                with open(flag_path, "w") as f:
                    f.write("1")
            except Exception:
                pass

            _, save_yaml = _get_yaml_utils()
            active_p = self._model.ai.active_personality if hasattr(self._model, "ai") else "Unknown"
            logger.info(f"[CONFIG] Attempting to write to YAML. Active Personality in Model: {active_p}")
            save_yaml(self._yaml_path, self._model)
            self._sync_dict()

            new_lang = self._model.language
            if new_lang and new_lang != old_lang:
                try:
                    from zentra.core.i18n import translator
                    translator.get_translator().set_language(new_lang)
                    logger.info(f"[CONFIG] Language updated to: {new_lang}")
                except Exception:
                    pass

            logger.info("[CONFIG] Configuration saved successfully.")
            return True
        except Exception as e:
            logger.error(f"[CONFIG] Save error: {e}")
            return False

    def get(self, *keys, default=None):
        """Get a nested value, e.g. config.get('backend', 'type')"""
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
        """Set a nested value, e.g. config.set('ollama', 'backend', 'type')"""
        if len(keys) == 0:
            return False
        # Update the plain dict
        target = self.config
        for key in keys[:-1]:
            if key not in target:
                target[key] = {}
            target = target[key]
        target[keys[-1]] = value
        # Re-validate the model from the updated dict to keep them in sync
        try:
            SystemConfig = _get_schema()
            self._model = SystemConfig.model_validate(self.config)
        except Exception:
            pass  # Keep dict change even if model can't fully validate
        return True

    def reload(self):
        """Reload the configuration from the YAML file."""
        self._model = self._load_model()
        self._sync_dict()
        return self.config

    def update_config(self, new_data: dict):
        """Deep merge new_data into current config and save."""
        logger.info(f"[CONFIG-CORE] update_config CALLED with: {new_data.get('ai', {}).get('active_personality')}")
        self.reload()
        self._deep_update(self.config, new_data)
        try:
            SystemConfig = _get_schema()
            # Attempt validation
            new_model = SystemConfig.model_validate(self.config)
            
            # MANUAL SYNC CHECK
            if hasattr(new_model, 'ai') and 'ai' in new_data and 'active_personality' in new_data['ai']:
                logger.info(f"[CONFIG-CORE] Force setting active_personality to: {new_data['ai']['active_personality']}")
                new_model.ai.active_personality = new_data['ai']['active_personality']
            
            self._model = new_model
            self._sync_dict() 
            res = self.save()
            return res
        except Exception as e:
            import traceback
            logger.error(f"[CONFIG-CORE] CRITICAL ERROR during update_config: {e}")
            logger.error(traceback.format_exc())
            return False

    def _deep_update(self, base: dict, patch: dict):
        for k, v in patch.items():
            if isinstance(v, dict) and k in base and isinstance(base[k], dict):
                self._deep_update(base[k], v)
            else:
                base[k] = v

    def get_plugin_config(self, plugin_tag: str, key=None, default=None):
        """Returns the config dict (or a key) for a given plugin."""
        plugins = self.config.get("plugins", {})
        plugin_cfg = plugins.get(plugin_tag, {})
        if key is None:
            return plugin_cfg
        return plugin_cfg.get(key, default)

    def set_plugin_config(self, plugin_tag: str, key: str, value):
        """Sets a plugin config value and saves."""
        if "plugins" not in self.config:
            self.config["plugins"] = {}
        if plugin_tag not in self.config["plugins"]:
            self.config["plugins"][plugin_tag] = {}
        self.config["plugins"][plugin_tag][key] = value
        try:
            SystemConfig = _get_schema()
            self._model = SystemConfig.model_validate(self.config)
        except Exception:
            pass
        self.save()

    def sync_available_personalities(self):
        """
        Scans the 'personality' folder for .yaml files and updates
        'ai.available_personalities' if the list has changed.
        Returns the current list of personality files.
        """
        import os
        import glob
        folder = _os.path.join(_PROJECT_ROOT, "zentra", "personality")
        if not _os.path.exists(folder):
            try:
                _os.makedirs(folder)
            except Exception:
                pass

        # 1. Get all YAML files and sort them alphabetically
        files = sorted([_os.path.basename(f) for f in glob.glob(_os.path.join(folder, "*.yaml"))])

        if files:
            # 2. Force Zentra_System_Soul to position #1 if present
            primary = "Zentra_System_Soul.yaml"
            if primary in files:
                files.remove(primary)
                files.insert(0, primary)

            # 3. Create the mapping dictionary
            personality_dict = {str(i + 1): name for i, name in enumerate(files)}
            current_dict = self.config.get("ai", {}).get("available_personalities", {})
            
            # --- ROBUST FALLBACK CHECK ---
            active = self.config.get("ai", {}).get("active_personality")
            # Case-insensitive comparison
            files_lower = [f.lower() for f in files]
            if active and active.lower() not in files_lower:
                logger.warning(f"[CONFIG] Active personality '{active}' not found in filesystem. Reverting to {primary}.")
                self.set(primary, "ai", "active_personality")

            # 4. Save if the list changed or if we reverted the active one
            if personality_dict != current_dict or (active and active.lower() not in files_lower):
                self.set(personality_dict, "ai", "available_personalities")
                self.save()
                logger.info("[CONFIG] Personality list synchronized with filesystem.")

        return files