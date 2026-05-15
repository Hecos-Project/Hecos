"""
MODULE: Config Manager
DESCRIPTION: Loads, validates and saves Hecos configuration from multiple YAML files.

Layer architecture:
  L0  config/data/system.yaml      → SystemConfig
  L0b config/data/agent.yaml       → AgentConfig       (via AgentConfig routes, not here)
  L0c config/data/audio.yaml       → AudioConfig       (via audio_config module)
  L0d config/data/media.yaml       → MediaConfig       (via media_config module)
  L0e config/data/keys.yaml        → KeysConfig        (via key_manager module)
  L0f config/data/routing_overrides.yaml → RoutingOverrides  (via routes_config)
  L1  config/data/plugins.yaml     → PluginsFileConfig (plugins + extensions)
  L2  config/data/widgets.yaml     → WidgetsFileConfig (widgets)

The `self.config` dict is a UNIFIED flat view of L0 + L1 + L2 for backward compatibility.
All saves correctly split data back to the appropriate files.
"""

import os as _os
import json
import time
import threading
from hecos.core.logging import logger


def _get_yaml_utils():
    from hecos.config.yaml_utils import load_yaml, save_yaml, save_dict_to_yaml, load_dict_from_yaml, _deep_merge
    return load_yaml, save_yaml, save_dict_to_yaml, load_dict_from_yaml, _deep_merge


def _get_system_schema():
    from hecos.config.schemas.system_schema import SystemConfig
    return SystemConfig


def _get_plugins_schema():
    from hecos.config.schemas.plugins_schema import PluginsFileConfig
    return PluginsFileConfig


def _get_widgets_schema():
    from hecos.config.schemas.widgets_schema import WidgetsFileConfig
    return WidgetsFileConfig


_PROJECT_ROOT = _os.path.abspath(_os.path.normpath(_os.path.join(_os.path.dirname(__file__), "..", "..")))
_HECOS_DIR = _os.path.abspath(_os.path.normpath(_os.path.join(_PROJECT_ROOT, "hecos")))

_CONFIG_YAML_PATH    = _os.path.join(_HECOS_DIR, "config", "data", "system.yaml")
_CONFIG_JSON_PATH    = _os.path.join(_HECOS_DIR, "config", "data", "system.json")
_PLUGINS_YAML_PATH   = _os.path.join(_HECOS_DIR, "config", "data", "plugins.yaml")
_WIDGETS_YAML_PATH   = _os.path.join(_HECOS_DIR, "config", "data", "widgets.yaml")


class ConfigManager:
    def __init__(self, config_path=None):
        # config_path kept for backward compat
        if config_path is not None:
            base = _os.path.splitext(config_path)[0]
            self._yaml_path = base + ".yaml"
            self._json_path = config_path
        else:
            self._yaml_path = _CONFIG_YAML_PATH
            self._json_path = _CONFIG_JSON_PATH

        data_dir = _os.path.dirname(self._yaml_path)
        self._plugins_path = _os.path.join(data_dir, "plugins.yaml")
        self._widgets_path = _os.path.join(data_dir, "widgets.yaml")

        self._lock = threading.RLock()  # Reentrant: update_config holds lock, then calls save() which also acquires it
        self._ensure_files_exist()
        self._load_all()

    def _ensure_files_exist(self):
        """Auto-generate config files from templates if missing."""
        import shutil
        data_dir = _os.path.dirname(self._yaml_path)

        files_to_check = [
            "system.yaml",
            "plugins.yaml",
            "widgets.yaml",
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

        env_file = _os.path.join(_HECOS_DIR, ".env")
        env_example = env_file + ".example"
        if not _os.path.exists(env_file) and _os.path.exists(env_example):
            try:
                import shutil
                shutil.copy2(env_example, env_file)
                logger.info("[CONFIG] Auto-generated .env from template.")
            except Exception as e:
                logger.error(f"[CONFIG] Failed to auto-generate .env: {e}")


    # ──────────────────────────────────────────────────────────────────────────
    # INTERNAL LOAD / SAVE
    # ──────────────────────────────────────────────────────────────────────────

    def _load_all(self):
        """Load all config layers and build the unified self.config dict."""
        load_yaml, _, _, _, _ = _get_yaml_utils()
        SystemConfig     = _get_system_schema()
        PluginsFileConfig = _get_plugins_schema()
        WidgetsFileConfig = _get_widgets_schema()

        # --- L0: system.yaml ---
        try:
            self._system_model = load_yaml(self._yaml_path, SystemConfig)
        except Exception as e:
            logger.error(f"[CONFIG] Failed to load system.yaml: {e}. Using defaults.")
            self._system_model = SystemConfig()

        # --- L1: plugins.yaml ---
        try:
            self._plugins_model = load_yaml(self._plugins_path, PluginsFileConfig)
        except Exception as e:
            logger.error(f"[CONFIG] Failed to load plugins.yaml: {e}. Using defaults.")
            self._plugins_model = PluginsFileConfig()

        # --- L2: widgets.yaml ---
        try:
            self._widgets_model = load_yaml(self._widgets_path, WidgetsFileConfig)
        except Exception as e:
            logger.error(f"[CONFIG] Failed to load widgets.yaml: {e}. Using defaults.")
            self._widgets_model = WidgetsFileConfig()

        self._apply_volatility()
        self._sync_dict()

    def _apply_volatility(self):
        """Clear volatile fields that should NOT persist across restarts.

        Rules:
          - `special_instructions` (custom prompt append): volatile. Cleared on
            restart unless `save_special_instructions` is True.
          - `safety_instructions` (persistent safety/context disclaimer): NEVER
            cleared automatically — always persisted from YAML.
        """
        if not self._system_model.ai.save_special_instructions:
            self._system_model.ai.special_instructions = ""
        # safety_instructions is intentionally NOT cleared here — it is a
        # persistent configuration value, not a session-scoped field.

    def _sync_dict(self):
        """Rebuild the unified self.config dict from the three typed models."""
        system_dict  = self._system_model.model_dump()
        plugins_dict = self._plugins_model.model_dump()
        widgets_dict = self._widgets_model.model_dump()

        # Remove the legacy `agent:` absorption key — it's NOT part of the saved system config
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

    # ──────────────────────────────────────────────────────────────────────────
    # PUBLIC API
    # ──────────────────────────────────────────────────────────────────────────

    def save(self):
        """Persist the current in-memory config to all three YAML files.
        Thread-safe: uses self._lock to prevent concurrent writes.
        """
        with self._lock:
          try:
            # Write app-flag so monitor.py doesn't trigger a restart
            try:
                flag_path = _os.path.join(_PROJECT_ROOT, ".config_saved_by_app")
                with open(flag_path, "w") as f:
                    f.write("1")
                time.sleep(0.05)
            except Exception:
                pass

            SystemConfig      = _get_system_schema()
            PluginsFileConfig = _get_plugins_schema()
            WidgetsFileConfig = _get_widgets_schema()

            # --- Rebuild models from unified self.config (source of truth) ---
            # Extract the three domains from the flat dict
            system_dict  = {k: v for k, v in self.config.items()
                            if k not in ("plugins", "extensions", "widgets")}
            plugins_dict = {
                "plugins":    self.config.get("plugins", {}),
                "extensions": self.config.get("extensions", {}),
            }
            widgets_dict = {
                "widgets": self.config.get("widgets", {}),
            }

            # Validate each domain
            try:
                self._system_model  = SystemConfig.model_validate(system_dict)
            except Exception as e:
                logger.error(f"[CONFIG] system.yaml validation failed: {e}")
                return False

            try:
                self._plugins_model = PluginsFileConfig.model_validate(plugins_dict)
            except Exception as e:
                logger.error(f"[CONFIG] plugins.yaml validation failed: {e}")
                return False

            try:
                self._widgets_model = WidgetsFileConfig.model_validate(widgets_dict)
            except Exception as e:
                logger.error(f"[CONFIG] widgets.yaml validation failed: {e}")
                return False

            from hecos.config.yaml_utils import save_yaml

            # --- Save L0 (system only — no agent/plugins/widgets) ---
            system_save_dict = self._system_model.model_dump()
            system_save_dict.pop("agent", None)  # never write agent block to system.yaml
            from hecos.config.yaml_utils import save_dict_to_yaml
            save_dict_to_yaml(self._yaml_path, system_save_dict)

            # --- Save L1 ---
            # TRACE: log calendar state just before writing to disk
            try:
                _cal_locale = self._plugins_model.extensions.calendar.calendar_locale
                _cal_country = self._plugins_model.extensions.calendar.calendar_country
                logger.debug(f"[CAL-TRACE] About to write plugins.yaml — calendar_locale={_cal_locale!r} calendar_country={_cal_country!r}")
            except Exception:
                pass
            save_yaml(self._plugins_path, self._plugins_model)

            # --- Save L2 ---
            save_yaml(self._widgets_path, self._widgets_model)

            # Keep unified dict in sync
            self._sync_dict()

            # Runtime language update
            new_lang = self._system_model.language
            if new_lang:
                try:
                    from hecos.core.i18n import translator
                    t_inst = translator.get_translator()
                    if t_inst.language != new_lang:
                        t_inst.set_language(new_lang)
                        logger.info(f"[CONFIG] Language runtime updated to: {new_lang}")
                except Exception:
                    pass

            logger.info("[CONFIG] Configuration saved successfully.")
            return True

          except Exception as e:
            import traceback
            logger.error(f"[CONFIG] Save error: {e}")
            logger.error(traceback.format_exc())
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
        """Set a nested value in the unified config dict.
        e.g. config.set('ollama', 'backend', 'type')
        """
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
        """Reload ALL config files from disk.
        Thread-safe: waits for any in-progress save to complete before reloading.
        """
        with self._lock:
            self._load_all()
        return self.config

    def update_config(self, new_data: dict):
        """Deep merge new_data into the in-memory config, validate, then save.

        Thread-safe: holds RLock for the full operation (copy → merge → validate
        → commit → save) to prevent concurrent writes from corrupting self.config.
        RLock is reentrant so save() can acquire it again without deadlocking.
        """
        import copy
        with self._lock:
          try:
            temp_config = copy.deepcopy(self.config)
            self._deep_update(temp_config, new_data)

            SystemConfig      = _get_system_schema()
            PluginsFileConfig = _get_plugins_schema()
            WidgetsFileConfig = _get_widgets_schema()

            system_dict = {k: v for k, v in temp_config.items()
                           if k not in ("plugins", "extensions", "widgets")}
            plugins_dict = {
                "plugins":    temp_config.get("plugins", {}),
                "extensions": temp_config.get("extensions", {}),
            }
            widgets_dict = {"widgets": temp_config.get("widgets", {})}

            new_system  = SystemConfig.model_validate(system_dict)
            new_plugins = PluginsFileConfig.model_validate(plugins_dict)
            new_widgets = WidgetsFileConfig.model_validate(widgets_dict)

            if hasattr(new_system, 'ai') and 'ai' in new_data and 'active_personality' in new_data['ai']:
                new_system.ai.active_personality = new_data['ai']['active_personality']

            self._system_model  = new_system
            self._plugins_model = new_plugins
            self._widgets_model = new_widgets
            self._sync_dict()

            return self.save()

          except Exception as e:
            import traceback
            logger.error(f"[CONFIG] CRITICAL ERROR during update_config (aborted): {e}")
            logger.error(traceback.format_exc())
            return False

    def _deep_update(self, base: dict, patch: dict):
        for k, v in patch.items():
            if isinstance(v, dict) and k in base and isinstance(base[k], dict):
                self._deep_update(base[k], v)
            else:
                base[k] = v

    # ──────────────────────────────────────────────────────────────────────────
    # PLUGIN HELPERS
    # ──────────────────────────────────────────────────────────────────────────

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
        self.save()

    def get_extension_config(self, ext_name: str, key=None, default=None):
        """Returns the extensions config dict (or a key) for a given extension."""
        extensions = self.config.get("extensions", {})
        ext_cfg = extensions.get(ext_name, {})
        if key is None:
            return ext_cfg
        return ext_cfg.get(key, default)

    # ──────────────────────────────────────────────────────────────────────────
    # PERSONALITY SYNC
    # ──────────────────────────────────────────────────────────────────────────

    def sync_available_personalities(self):
        """
        Scans the 'personality' folder for .yaml files and updates
        'ai.available_personalities' if the list has changed.
        Returns the current list of personality files.
        """
        import glob
        folder = _os.path.join(_PROJECT_ROOT, "hecos", "personality")
        if not _os.path.exists(folder):
            try:
                _os.makedirs(folder)
            except Exception:
                pass

        files = sorted([_os.path.basename(f) for f in glob.glob(_os.path.join(folder, "*.yaml"))])

        if files:
            primary = "Hecos_System_Soul.yaml"
            if primary in files:
                files.remove(primary)
                files.insert(0, primary)

            personality_dict = {str(i + 1): name for i, name in enumerate(files)}
            current_dict = self.config.get("ai", {}).get("available_personalities", {})
            current_dict_str = {str(k): v for k, v in current_dict.items()} if isinstance(current_dict, dict) else {}

            active = self.config.get("ai", {}).get("active_personality")
            files_lower = [f.lower() for f in files]
            needs_revert = active and active.lower() not in files_lower

            if needs_revert:
                logger.warning(f"[CONFIG] Active personality '{active}' not found. Reverting to {primary}.")
                self.set(primary, "ai", "active_personality")

            if personality_dict != current_dict_str or needs_revert:
                self.set(personality_dict, "ai", "available_personalities")
                self.save()
                logger.info("[CONFIG] Personality list synchronized with filesystem.")

        return files