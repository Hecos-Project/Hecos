"""
MODULE: Plugin State
DESCRIPTION: Holds global state references for loaded plugins and their configurations.
"""

import os
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REGISTRY_PATH = os.path.join(_BASE_DIR, "core", "registry.json")

# Stores configuration schemas collected from plugins
_plugin_config_schemas = {}

# Active plugins (Native and Legacy)
_loaded_plugins = {}          # tag -> module (for JSON Calling / old single plugins)
_loaded_legacy_plugins = {}   # tag -> instance of LegacyPlugin class

# Lazy Load references
_lazy_plugins_paths = {}      # tag -> absolute path to main.py
_lazy_tool_schemas = {}       # Caches function calling schemas for dormant plugins

def get_active_tags():
    """Returns a list of all currently active plugin tags."""
    return list(_loaded_plugins.keys()) + list(_loaded_legacy_plugins.keys()) + list(_lazy_plugins_paths.keys())

def get_plugin_module(tag, legacy=False):
    """Returns the plugin module if active, or triggers a lazy load if dormant."""
    # 1. Quick check if already loaded
    if legacy:
        module = _loaded_legacy_plugins.get(tag)
    else:
        module = _loaded_plugins.get(tag)
    
    if module is not None:
        return module

    # 2. Just-In-Time (JIT) Import logic for dormant plugins
    if tag in _lazy_plugins_paths:
        import importlib.util
        import os
        from core.logging import logger
        
        main_file = _lazy_plugins_paths[tag]
        # Forced warning level for Yellow color in terminal as requested by user
        logger.warning(f"[LAZY LOAD] Awakening dormant plugin '{tag}' from {main_file}")
        
        try:
            plugin_dir = os.path.basename(os.path.dirname(main_file))
            module_name = f"plugins.{plugin_dir}.main"
            
            spec = importlib.util.spec_from_file_location(module_name, main_file)
            if spec:
                new_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(new_module)
                
                # Check if it was a legacy tool or class-based
                # Legacy usually has an 'info' and 'run' function, Native usually has a 'tools' class.
                is_legacy = hasattr(new_module, "info") and not hasattr(new_module, "tools")
                
                if is_legacy:
                    # For legacy, we might need to wrap it if the system expects an instance,
                    # but usually _loaded_legacy_plugins holds the module or instance.
                    # Zentra usually expects a class instance for class-based, or module for functional.
                    _loaded_legacy_plugins[tag] = new_module
                else:
                    _loaded_plugins[tag] = new_module
                    
                # Cache schemas if present (for future calls)
                if hasattr(new_module, "tools") and hasattr(new_module.tools, "config_schema"):
                    _plugin_config_schemas[tag] = new_module.tools.config_schema
                elif hasattr(new_module, "config_schema"):
                    _plugin_config_schemas[tag] = new_module.config_schema()
                    
                # Clean up lazy path reference
                del _lazy_plugins_paths[tag]
                
                # Return the correct one based on what was requested
                return _loaded_legacy_plugins.get(tag) if legacy else _loaded_plugins.get(tag)
                
        except Exception as e:
            logger.error(f"[LAZY LOAD] Failed to awaken plugin {tag}: {e}")
            
    return None
