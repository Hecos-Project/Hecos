"""
MODULE: Plugin Config Sync
DESCRIPTION: Synchronizes plugin configurations with the main config.json file.
"""

from hecos.core.logging import logger
from .module_state import _plugin_config_schemas

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

    updated_any = False
    for tag, schema in _plugin_config_schemas.items():
        plugin_cfg = config["plugins"].get(tag, {})
        plugin_updated = False

        # Ensure enabled is present (default True)
        if "enabled" not in plugin_cfg:
            plugin_cfg["enabled"] = True
            plugin_updated = True

        # Add any missing keys with default values
        for key, props in schema.items():
            if key not in plugin_cfg:
                plugin_cfg[key] = props.get("default")
                plugin_updated = True

        if plugin_updated:
            config["plugins"][tag] = plugin_cfg
            updated_any = True

    if updated_any:
        config_manager.save()
        logger.info(f"REGISTRY: Plugin configurations synchronized ({len(_plugin_config_schemas)} tools).")

    return config
