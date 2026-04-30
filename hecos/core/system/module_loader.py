"""
MODULE: Plugin Loader & Capability Registry - Hecos
DESCRIPTION: Facade module for plugin discovery, state management,
and documentation generation.
             Logic has been split into:
             - module_state.py
             - module_scanner.py
             - module_config_sync.py
             - module_docs.py
"""

from .module_state import (
    REGISTRY_PATH, 
    _plugin_config_schemas, 
    _loaded_plugins, 
    _loaded_legacy_plugins,
    get_active_tags, 
    get_plugin_module
)
from .module_scanner import update_capability_registry
from .module_config_sync import sync_plugin_config
from .module_docs import (
    get_formatted_capabilities, 
    generate_dynamic_guide,
    get_tools_schema, 
    get_legacy_schema
)
