"""
MODULE: Config Manager
DESCRIPTION: Loads, validates and saves the main system configuration.
             Uses YAML + Pydantic v2. Auto-migrates from legacy JSON on first run.
"""

import os as _os
import json
import time
from core.logging import logger

# Lazy imports (avoid circular imports at module level)
def _get_yaml_utils():
    from config.yaml_utils import load_yaml, save_yaml
    return load_yaml, save_yaml

def _get_schema():
    from config.schemas.system_schema import SystemConfig
    return SystemConfig

# Root of the project (parent of zentra/)
# __file__ is zentra/app/config.py -> dirname(dirname(dirname)) is root
_PROJECT_ROOT = _os.path.normpath(_os.path.join(_os.path.dirname(__file__), "..", ".."))
_CONFIG_YAML_PATH = _os.path.join(_PROJECT_ROOT, "config", "system.yaml")
_CONFIG_JSON_PATH = _os.path.join(_PROJECT_ROOT, "config", "system.json")


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

        self._model = self._load_model()
        self.config = self._model.model_dump()  # plain dict kept for full backward compat

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

    # ──────────────────────────────────────────────────────────────────────────
    # PUBLIC API
    # ──────────────────────────────────────────────────────────────────────────

    def save(self):
        """Serialize the current config to YAML and persist it."""
        try:
            old_lang = self.config.get("language")

            # Flag for monitor.py to avoid unnecessary restarts
            try:
                with open(".config_saved_by_app", "w") as f:
                    f.write("1")
            except Exception:
                pass

            _, save_yaml = _get_yaml_utils()
            save_yaml(self._yaml_path, self._model)
            self._sync_dict()

            new_lang = self._model.language
            if new_lang and new_lang != old_lang:
                try:
                    from core.i18n import translator
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
        self.reload()
        self._deep_update(self.config, new_data)
        try:
            SystemConfig = _get_schema()
            self._model = SystemConfig.model_validate(self.config)
        except Exception as e:
            logger.warning(f"[CONFIG] Validation warning after update: {e}")
        return self.save()

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
        Scans the 'personality' folder for .txt files and updates
        'ai.available_personalities' if the list has changed.
        Returns the current list of personality files.
        """
        import os
        import glob
        folder = "personality"
        if not os.path.exists(folder):
            try:
                os.makedirs(folder)
            except Exception:
                pass

        files = [os.path.basename(f) for f in glob.glob(os.path.join(folder, "*.txt"))]

        if files:
            personality_dict = {str(i + 1): name for i, name in enumerate(files)}
            current = self.get("ai", "available_personalities")
            if personality_dict != current:
                self.set(personality_dict, "ai", "available_personalities")
                self.save()
                logger.info("[CONFIG] Personality list synchronized with filesystem.")

        return files