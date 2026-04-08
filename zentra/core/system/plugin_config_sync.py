"""
MODULE: Plugin Config Sync
DESCRIPTION: Synchronizes plugin configurations with the main config.json file.
"""

from core.logging import logger
from .plugin_state import _plugin_config_schemas

def sync_plugin_config(config_manager=None):
    """
    Synchronizes plugin configurations with the config.json file.
    Adds missing sections with default values defined in the schemas.
    Also ensures each plugin has the 'enabled' key (default True).
    """
    if config_manager is None:
        from app.config import ConfigManager
        config_manager = ConfigManager()

    config = config_manager.config
    if "plugins" not in config:
        config["plugins"] = {}

    updated = False
    for tag, schema in _plugin_config_schemas.items():
        plugin_cfg = config["plugins"].get(tag, {})
        # Ensure enabled is present (default True)
        if "enabled" not in plugin_cfg:
            plugin_cfg["enabled"] = True
            updated = True
        # Add any missing keys with default values
        for key, props in schema.items():
            if key not in plugin_cfg:
                default = props.get("default")
                plugin_cfg[key] = default
                updated = True
        if updated:
            config["plugins"][tag] = plugin_cfg

    if updated:
        config_manager.save()
        logger.info("REGISTRY: Plugin configurations synchronized.")

    return config
