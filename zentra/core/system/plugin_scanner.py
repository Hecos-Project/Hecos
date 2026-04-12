"""
MODULE: Plugin Scanner
DESCRIPTION: Handles dynamic scanning of plugins (native and legacy) and
creation of the central JSON registry.
"""

import importlib.util
import sys
import os
import glob
import json
from zentra.core.logging import logger

from .plugin_state import (
    REGISTRY_PATH,
    _plugin_config_schemas,
    _loaded_plugins,
    _loaded_legacy_plugins,
    _lazy_plugins_paths
)

def update_capability_registry(config=None, debug_log=True):
    """
    Scans the plugins directory, queries the info() manifest, and
    generates a centralized JSON file with all active abilities.
    If config is passed, it uses it to check the 'enabled' flag.
    """
    _plugin_config_schemas.clear()
    _loaded_plugins.clear()
    _loaded_legacy_plugins.clear()
    _lazy_plugins_paths.clear()
    skills_map = {}

    # If we don't have config, load it (for backward compatibility)
    if config is None:
        try:
            from app.config import ConfigManager
            config = ConfigManager().config
        except ImportError:
            from zentra.app.config import ConfigManager
            config = ConfigManager().config

    # Determine the actual plugins directory
    # Try local 'plugins' first, then 'zentra/plugins'
    primary_plugins_dir = "plugins"
    if not os.path.exists(primary_plugins_dir):
        # We might be in package mode
        primary_plugins_dir = os.path.join("zentra", "plugins")
        if not os.path.exists(primary_plugins_dir):
            # Try absolute path from this file
            base = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
            primary_plugins_dir = os.path.join(base, "plugins")

    # Build list of all directories to scan
    scan_targets = []
    if os.path.exists(primary_plugins_dir):
        scan_targets.append(primary_plugins_dir)
        
    # Add external directories from config
    extra_dirs = config.get('plugins', {}).get('extra_dirs', [])
    for ed in extra_dirs:
        if os.path.exists(ed):
            scan_targets.append(ed)
        else:
            logger.warning(f"LOADER: Extra plugins directory not found: {ed}")

    for plugins_dir in scan_targets:
        if not os.path.isdir(plugins_dir): continue
        
        # Ensure the parent directory is in sys.path so 'plugins.xxx' works
        abs_p_dir = os.path.abspath(plugins_dir)
        parent_dir = os.path.dirname(abs_p_dir)
        if parent_dir not in sys.path:
            sys.path.append(parent_dir)
        # Also add the dir itself for direct imports if needed
        if abs_p_dir not in sys.path:
            sys.path.append(abs_p_dir)
            
        plugin_dirs = [d for d in os.listdir(plugins_dir)
                      if os.path.isdir(os.path.join(plugins_dir, d))
                      and not d.startswith("__")
                      and d != "plugins_disabled"]

        for plugin_dir in plugin_dirs:
            main_file = os.path.join(plugins_dir, plugin_dir, "main.py")
            manifest_file = os.path.join(plugins_dir, plugin_dir, "manifest.json")
            if not os.path.exists(main_file):
                # logger.debug("LOADER", f"Plugin {plugin_dir} without main.py, ignored")
                continue

            # --- NEW SECTION: LAZY LOADING via manifest.json ---
            if os.path.exists(manifest_file):
                try:
                    with open(manifest_file, "r", encoding="utf-8") as f:
                        manifest_data = json.load(f)
                    
                    tag = manifest_data.get("tag", "").upper()
                    if tag:
                        plugin_enabled = config.get('plugins', {}).get(tag, {}).get('enabled', True)
                        if not plugin_enabled:
                            if debug_log: logger.debug("LOADER", f"Plugin {plugin_dir} disabled by config.")
                            continue
                        
                        # Priorità alla configurazione utente, fallback sul manifest
                        is_lazy = config.get('plugins', {}).get(tag, {}).get('lazy_load', manifest_data.get("lazy_load", False))
                        
                        if is_lazy:
                            # Register capability without executing Python file
                            skills_map[tag] = {
                                "description": manifest_data.get("description", ""),
                                "commands": manifest_data.get("commands", {}),
                                "status": "ONLINE (DORMANT)",
                                "example": manifest_data.get("example", ""),
                                "routing_instructions": manifest_data.get("routing_instructions", ""),
                                "is_class_based": manifest_data.get("is_class_based", True),
                                "is_lazy": True
                            }
                            
                            _lazy_plugins_paths[tag] = os.path.abspath(main_file)
                            
                            # Cache the tool schema for LLM prompting without import
                            from .plugin_state import _lazy_tool_schemas
                            _lazy_tool_schemas[tag] = manifest_data.get("tool_schema", [])
                            
                            if debug_log: logger.debug("LOADER", f"Plugin {plugin_dir} registered efficiently (Lazy Load).")
                            continue # Skip the dynamic import section entirely
                            
                except Exception as e:
                    logger.error(f"LOADER: Failed to parse {manifest_file}, falling back to eager load: {e}")

            # --- EAGER LOADING (Backward compatibility or Critical Plugins) ---
            try:
                # Dynamic module import
                spec = importlib.util.spec_from_file_location(
                    f"plugins.{plugin_dir}.main",
                    main_file
                )
                if spec is None:
                    continue

                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Manifest extraction
                if hasattr(module, "tools"):
                    # --- NEW CLASS-BASED SYSTEM (FUNCTION CALLING) ---
                    tools_instance = module.tools
                    tag = tools_instance.tag
                    plugin_enabled = config.get('plugins', {}).get(tag, {}).get('enabled', True)
                    if not plugin_enabled:
                        if debug_log: logger.debug("LOADER", f"Plugin {plugin_dir} disabled by config.")
                        continue

                    _loaded_plugins[tag] = module
                    status = getattr(tools_instance, "status", "ONLINE")

                    # Extract commands by inspecting public methods
                    import inspect
                    commands = {}
                    for name, method in inspect.getmembers(tools_instance, predicate=inspect.ismethod):
                        if not name.startswith('_'):
                            doc = method.__doc__
                            commands[name] = doc.strip().split('\n')[0] if doc else "Method"

                    skills_map[tag] = {
                        "description": tools_instance.desc,
                        "commands": commands,
                        "status": status,
                        "example": "",
                        "routing_instructions": getattr(tools_instance, "routing_instructions", ""),
                        "is_class_based": True
                    }
                    logger.debug("LOADER", f"Class-based Plugin {plugin_dir} loaded with tag {tag}")

                    if hasattr(tools_instance, "config_schema"):
                        _plugin_config_schemas[tag] = tools_instance.config_schema

                elif hasattr(module, "info"):
                    # --- OLD LEGACY SYSTEM ---
                    plugin_info = module.info()
                    tag = plugin_info['tag']
                    # Check enabled flag
                    plugin_enabled = config.get('plugins', {}).get(tag, {}).get('enabled', True)
                    if not plugin_enabled:
                        if debug_log: logger.debug("LOADER", f"Plugin {plugin_dir} disabled by config.")
                        continue

                    # Save module and load
                    _loaded_plugins[tag] = module

                    status = module.status() if hasattr(module, "status") else "ONLINE"

                    skills_map[tag] = {
                        "description": plugin_info.get('desc') or plugin_info.get('description', ''),
                        "commands": plugin_info.get('comandi') or plugin_info.get('commands', {}),
                        "status": status,
                        "example": plugin_info.get("esempio") or plugin_info.get("example", ""),
                        "routing_instructions": plugin_info.get("routing_instructions", "")
                    }
                    logger.debug("LOADER", f"Plugin {plugin_dir} loaded with tag {tag}")

                    # Collect configuration schema if present
                    if hasattr(module, "config_schema"):
                        _plugin_config_schemas[tag] = module.config_schema()
                        logger.debug("LOADER", f"Plugin {plugin_dir} has config_schema")

            except Exception as e:
                logger.error(f"LOADER: Failed to load {plugin_dir}: {e}")
                continue

    # --- NEW SECTION: Load Legacy Plugins from plugins_legacy/ folder ---
    legacy_root = "plugins_legacy"
    if not os.path.exists(legacy_root):
        legacy_root = os.path.join("zentra", "plugins_legacy")

    if os.path.exists(legacy_root):
        legacy_dirs = [d for d in os.listdir(legacy_root)
                      if os.path.isdir(os.path.join(legacy_root, d))
                      and not d.startswith("__")]

        for legacy_dir in legacy_dirs:
            main_file = os.path.join(legacy_root, legacy_dir, "main.py")
            if not os.path.exists(main_file):
                continue

            try:
                spec = importlib.util.spec_from_file_location(
                    f"plugins_legacy.{legacy_dir}.main",
                    main_file
                )
                if spec is None: continue
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Look for a class ending in 'Plugin' or instantiate via get_plugin()
                legacy_instance = None
                if hasattr(module, "get_plugin"):
                    legacy_instance = module.get_plugin()
                else:
                    import inspect
                    for name, obj in inspect.getmembers(module, inspect.isclass):
                        if name.endswith("Plugin") and obj.__module__ == module.__name__:
                            legacy_instance = obj()
                            break

                if legacy_instance and hasattr(legacy_instance, "info"):
                    plugin_info = legacy_instance.info()
                    tag = plugin_info['tag']

                    plugin_enabled = config.get('plugins', {}).get(tag, {}).get('enabled', True)
                    if not plugin_enabled:
                        if debug_log: logger.debug("LOADER", f"Legacy Plugin {legacy_dir} disabled by config.")
                        continue

                    _loaded_legacy_plugins[tag] = legacy_instance
                    status = legacy_instance.status() if hasattr(legacy_instance, "status") else "ONLINE"

                    # Extraction of commands with prioritization for English nomenclature
                    info_dict = legacy_instance.info()
                    legacy_commands = info_dict.get('commands') or info_dict.get('comandi', {})

                    skills_map[tag] = {
                        "description": info_dict.get('description') or info_dict.get('desc', ''),
                        "commands": legacy_commands,
                        "status": status,
                        "example": info_dict.get("example") or info_dict.get("esempio", ""),
                        "is_legacy": True
                    }
                    if debug_log: logger.debug("LOADER", f"OOP Legacy Plugin {legacy_dir} loaded with tag {tag}")
            except Exception as e:
                logger.error(f"LOADER: Failed to load OOP Legacy {legacy_dir}: {e}")
                continue

    # 2. (Optional) Search also in the old structure for compatibility
    old_plugins_files = glob.glob(os.path.join(plugins_dir, "*.py"))
    for file in old_plugins_files:
        module_name = os.path.basename(file)[:-3]
        if module_name.startswith("__") or module_name.startswith("_"):
            continue

        # Avoid reloading plugins already found in the new structure
        if any(module_name == d for d in plugin_dirs):
            continue

        try:
            spec = importlib.util.spec_from_file_location(module_name, file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            if hasattr(module, "info"):
                plugin_info = module.info()
                tag = plugin_info['tag']

                # Check enabled flag
                plugin_enabled = config.get('plugins', {}).get(tag, {}).get('enabled', True)
                if not plugin_enabled:
                    logger.debug("LOADER", f"Legacy plugin {module_name} disabled, ignored.")
                    continue

                status = module.status() if hasattr(module, "status") else "ONLINE"

                skills_map[tag] = {
                    "description": plugin_info.get('desc') or plugin_info.get('description', ''),
                    "commands": plugin_info.get('comandi') or plugin_info.get('commands', {}),
                    "status": status,
                    "example": plugin_info.get("esempio") or plugin_info.get("example", "")
                }
                logger.debug("LOADER", f"Legacy plugin {module_name} loaded with tag {tag}")

                if hasattr(module, "config_schema"):
                    _plugin_config_schemas[tag] = module.config_schema()
                    logger.debug("LOADER", f"Legacy plugin {module_name} has config_schema")

        except Exception as e:
            logger.error(f"LOADER: Failed to load legacy {module_name}: {e}")
            continue

    # --- NEW SECTION: Universal Hub - External Providers (MCP) ---
    try:
        mcp_cfg = config.get("plugins", {}).get("MCP_BRIDGE", {})
        if mcp_cfg.get("enabled", True):
            mcp_servers = mcp_cfg.get("servers", {})
            for mcp_name, mcp_s in mcp_servers.items():
                if mcp_s.get("enabled", True):
                    # We map each external MCP server as a top-level module in Zentra
                    skills_map[f"MCP_{mcp_name.upper()}"] = {
                        "description": f"External Tool Provider ({mcp_name}) via Model Context Protocol.",
                        "commands": {"<dynamic_tools>": "Tools are dynamically discovered upon connection."},
                        "status": "EXTERNAL",
                        "example": "",
                        "routing_instructions": "Native LLM Function Calling exposed seamlessly.",
                        "is_class_based": False,
                        "is_mcp": True,
                        "server_name": mcp_name
                    }
                    if debug_log: logger.debug("LOADER", f"External Provider {mcp_name} registered in unified hub.")
    except Exception as e:
        logger.error(f"LOADER: Failed to parse MCP external providers for registry: {e}")

    # Centralized registry writing
    try:
        with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
            json.dump(skills_map, f, indent=4, ensure_ascii=False)
        if debug_log:
            logger.info(f"REGISTRY: Capabilities registry updated ({len(skills_map)} modules).")
    except Exception as e:
        logger.error(f"REGISTRY: File write error: {e}")

    return skills_map
