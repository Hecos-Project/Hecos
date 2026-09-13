"""
MODULE: Config Manager
DESCRIPTION: Loads, validates and saves Hecos configuration from multiple YAML files.

Layer architecture:
  L0  config/data/system.yaml      → SystemConfig
  L1  config/data/plugins.yaml     → PluginsFileConfig (plugins + extensions)
  L2  config/data/widgets.yaml     → WidgetsFileConfig (widgets)

The `self.config` dict is a UNIFIED flat view of L0 + L1 + L2 for backward compatibility.
All saves correctly split data back to the appropriate files.
"""

import os
import threading
from hecos.core.logging import logger

_PROJECT_ROOT = os.path.abspath(os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..")))
_HECOS_DIR = os.path.abspath(os.path.normpath(os.path.join(_PROJECT_ROOT, "hecos")))

_CONFIG_YAML_PATH    = os.path.join(_HECOS_DIR, "config", "data", "system.yaml")
_CONFIG_JSON_PATH    = os.path.join(_HECOS_DIR, "config", "data", "system.json")
_PLUGINS_YAML_PATH   = os.path.join(_HECOS_DIR, "config", "data", "plugins.yaml")
_WIDGETS_YAML_PATH   = os.path.join(_HECOS_DIR, "config", "data", "widgets.yaml")


class ConfigManager:
    def __init__(self, config_path=None):
        if config_path is not None:
            base = os.path.splitext(config_path)[0]
            self._yaml_path = base + ".yaml"
            self._json_path = config_path
        else:
            self._yaml_path = _CONFIG_YAML_PATH
            self._json_path = _CONFIG_JSON_PATH

        data_dir = os.path.dirname(self._yaml_path)
        self._plugins_path = os.path.join(data_dir, "plugins.yaml")
        self._widgets_path = os.path.join(data_dir, "widgets.yaml")

        self._lock = threading.RLock()
        self._ensure_files_exist()
        self._load_all()

    def _ensure_files_exist(self):
        from hecos.app.config_utils import ensure_files_exist
        ensure_files_exist(self._yaml_path, _HECOS_DIR)

    def _load_all(self):
        from hecos.app.config_io import load_config_models
        from hecos.app.config_utils import sanitize_widgets_yaml
        
        self._system_model, self._plugins_model, self._widgets_model = load_config_models(
            self._yaml_path, self._plugins_path, self._widgets_path
        )
        
        self._apply_volatility()

        # Try to sanitize widgets
        if sanitize_widgets_yaml(self._widgets_path, _HECOS_DIR):
            # Reload if modified
            self._system_model, self._plugins_model, self._widgets_model = load_config_models(
                self._yaml_path, self._plugins_path, self._widgets_path
            )

        self._sync_dict()

    def _apply_volatility(self):
        if hasattr(self._system_model, 'ai') and not getattr(self._system_model.ai, 'save_special_instructions', False):
            self._system_model.ai.special_instructions = ""

    def _sync_dict(self):
        system_dict  = self._system_model.model_dump()
        plugins_dict = self._plugins_model.model_dump()
        widgets_dict = self._widgets_model.model_dump()

        system_dict.pop("agent", None)

        self.config = {
            **system_dict,
            "plugins":    plugins_dict.get("plugins", {}),
            "extensions": plugins_dict.get("extensions", {}),
            "widgets":    widgets_dict.get("widgets", {}),
        }

    @property
    def yaml_path(self):
        return self._yaml_path

    def save(self):
        with self._lock:
            try:
                from hecos.app.config_io import save_config
                success, s_model, p_model, w_model = save_config(
                    self._yaml_path, self._plugins_path, self._widgets_path,
                    self.config, _PROJECT_ROOT
                )
                
                if success:
                    self._system_model = s_model
                    self._plugins_model = p_model
                    self._widgets_model = w_model
                    self._sync_dict()
                    return True
                return False
            except Exception as e:
                import traceback
                logger.error(f"[CONFIG] Save error: {e}")
                logger.error(traceback.format_exc())
                return False

    def get(self, *keys, default=None):
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
        with self._lock:
            self._load_all()
        return self.config

    def update_config(self, new_data: dict):
        with self._lock:
            try:
                from hecos.app.config_io import update_config_logic
                
                temp_config, new_system, new_plugins, new_widgets = update_config_logic(self.config, new_data)
                
                self._system_model  = new_system
                self._plugins_model = new_plugins
                self._widgets_model = new_widgets
                
                # Update config with the modified temp config 
                # (save() will build it back up, but let's sync first to be safe)
                self.config = temp_config
                self._sync_dict()

                return self.save()
            except Exception as e:
                import traceback
                logger.error(f"[CONFIG] CRITICAL ERROR during update_config (aborted): {e}")
                logger.error(traceback.format_exc())
                return False

    def update_from_webui(self, new_data: dict):
        """Alias of update_config — called by web UI REST endpoints.
        Deep merges new_data into the in-memory config, validates, then saves.
        """
        return self.update_config(new_data)

    def _deep_update(self, base: dict, patch: dict):
        """Deep merge helper — kept for backward compatibility."""
        from hecos.app.config_io import deep_update
        deep_update(base, patch)

    def get_plugin_config(self, plugin_tag: str, key=None, default=None):
        plugins = self.config.get("plugins", {})
        plugin_cfg = plugins.get(plugin_tag, {})
        if key is None:
            return plugin_cfg
        return plugin_cfg.get(key, default)

    def set_plugin_config(self, plugin_tag: str, key: str, value):
        if "plugins" not in self.config:
            self.config["plugins"] = {}
        if plugin_tag not in self.config["plugins"]:
            self.config["plugins"][plugin_tag] = {}
        self.config["plugins"][plugin_tag][key] = value
        self.save()

    def get_extension_config(self, ext_name: str, key=None, default=None):
        extensions = self.config.get("extensions", {})
        ext_cfg = extensions.get(ext_name, {})
        if key is None:
            return ext_cfg
        return ext_cfg.get(key, default)

    def sync_available_personalities(self):
        from hecos.app.config_utils import sync_available_personalities
        return sync_available_personalities(self.config, _PROJECT_ROOT, self.set, self.save)