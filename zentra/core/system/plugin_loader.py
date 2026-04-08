"""
MODULE: Plugin Loader & Capability Registry - Zentra Core
DESCRIPTION: Facade module for plugin discovery, state management,
and documentation generation.
             Logic has been split into:
             - plugin_state.py
             - plugin_scanner.py
             - plugin_config_sync.py
             - plugin_docs.py
"""

from .plugin_state import (
    REGISTRY_PATH, 
    _plugin_config_schemas, 
    _loaded_plugins, 
    _loaded_legacy_plugins,
    get_active_tags, 
    get_plugin_module
)
from .plugin_scanner import update_capability_registry
from .plugin_config_sync import sync_plugin_config
from .plugin_docs import (
    get_formatted_capabilities, 
    generate_dynamic_guide,
    get_tools_schema, 
    get_legacy_schema
)
