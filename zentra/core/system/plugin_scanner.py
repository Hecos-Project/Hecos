"""
MODULE: Plugin Scanner
DESCRIPTION: Handles dynamic scanning of plugins (native and legacy) and
creation of the central JSON registry.
Supports multi-source plugin discovery via `system.plugin_sources` config.
"""

import importlib.util
import os
import sys
import types
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

def _load_plugin_from_file(plugin_dir, main_file, PLUGINS_DIR, config, skills_map, debug_log):
    """
    Loads a single plugin folder via eager import.
    Handles both class-based (tools) and legacy (info()) plugin styles.
    """
    # Internal plugins (inside zentra/plugins/) keep their proper package name
    # so that relative imports (from .server import ...) work correctly.
    # External plugins get a unique name to avoid collisions.
    import zentra as _z_pkg
    _default_plugins = os.path.abspath(os.path.join(os.path.dirname(_z_pkg.__file__), "plugins"))
    if os.path.abspath(PLUGINS_DIR) == _default_plugins:
        module_id = f"zentra.plugins.{plugin_dir}.main"
        # Ensure the parent package exists in sys.modules for relative imports to work
        pkg_name = f"zentra.plugins.{plugin_dir}"
        if pkg_name not in sys.modules:
            pkg = types.ModuleType(pkg_name)
            pkg.__path__ = [os.path.join(PLUGINS_DIR, plugin_dir)]
            pkg.__package__ = pkg_name
            sys.modules[pkg_name] = pkg
    else:
        module_id = f"ext_plugin_{plugin_dir}_{hash(PLUGINS_DIR) & 0xffff}"

    try:
        spec = importlib.util.spec_from_file_location(module_id, main_file)
        if spec is None:
            return

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_id] = module  # Register before exec for circular-safe imports
        spec.loader.exec_module(module)

        # --- CLASS-BASED SYSTEM (FUNCTION CALLING) ---
        if hasattr(module, "tools"):
            tools_instance = module.tools
            tag = tools_instance.tag
            plugin_enabled = config.get('plugins', {}).get(tag, {}).get('enabled', True)
            if not plugin_enabled:
                if debug_log: logger.debug("LOADER", f"Plugin {plugin_dir} disabled by config.")
                return

            _loaded_plugins[tag] = module
            status = getattr(tools_instance, "status", "ONLINE")

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
                "is_class_based": True
            }
            logger.debug("LOADER", f"Class-based Plugin {plugin_dir} loaded with tag {tag}")

            if hasattr(tools_instance, "config_schema"):
                _plugin_config_schemas[tag] = tools_instance.config_schema

        # --- OLD LEGACY SYSTEM ---
        elif hasattr(module, "info"):
            plugin_info = module.info()
            tag = plugin_info['tag']
            plugin_enabled = config.get('plugins', {}).get(tag, {}).get('enabled', True)
            if not plugin_enabled:
                if debug_log: logger.debug("LOADER", f"Plugin {plugin_dir} disabled by config.")
                return

            _loaded_plugins[tag] = module
            status = module.status() if hasattr(module, "status") else "ONLINE"

            skills_map[tag] = {
                "description": plugin_info.get('desc') or plugin_info.get('description', ''),
                "commands": plugin_info.get('comandi') or plugin_info.get('commands', {}),
                "status": status,
                "example": plugin_info.get("esempio") or plugin_info.get("example", "")
            }
            logger.debug("LOADER", f"Plugin {plugin_dir} loaded with tag {tag}")

            if hasattr(module, "config_schema"):
                _plugin_config_schemas[tag] = module.config_schema()

    except Exception as e:
        logger.error(f"LOADER: Failed to load {plugin_dir}: {e}")


def update_capability_registry(config=None, debug_log=True):
    """
    Scans all configured plugin source directories, queries manifests, and
    generates a centralized JSON file with all active capabilities.
    Supports internal (zentra/plugins) and external (Elite, Cognitive Lab) sources.
    """
    _plugin_config_schemas.clear()
    _loaded_plugins.clear()
    _loaded_legacy_plugins.clear()
    _lazy_plugins_paths.clear()
    skills_map = {}

    if config is None:
        from zentra.app.config import ConfigManager
        config = ConfigManager().config

    import zentra
    ZENTRA_DIR = os.path.dirname(zentra.__file__)

    # --- RESOLVE PLUGIN SOURCE PATHS ---
    sources = config.get('system', {}).get('plugin_sources', [])
    if not sources:
        sources = ["zentra/plugins"]  # Fallback to default

    project_root = os.path.abspath(os.path.join(ZENTRA_DIR, ".."))
    search_paths = []

    for src in sources:
        if os.path.isabs(src):
            p = src
        else:
            p = os.path.normpath(os.path.join(project_root, src))

        logger.info(f"LOADER: Resolved source '{src}' -> '{p}'")

        if os.path.exists(p) and os.path.isdir(p):
            search_paths.append(p)
        else:
            if debug_log: logger.warning("LOADER", f"Plugin source path not found, skipping: {p}")

    # --- SCAN EACH SOURCE ---
    for PLUGINS_DIR in search_paths:
        if debug_log: logger.debug("LOADER", f"Scanning plugin source: {PLUGINS_DIR}")

        try:
            plugin_dirs = [d for d in os.listdir(PLUGINS_DIR)
                          if os.path.isdir(os.path.join(PLUGINS_DIR, d))
                          and not d.startswith("__")
                          and d != "plugins_disabled"]
        except Exception as e:
            logger.error(f"LOADER: Error reading plugin source {PLUGINS_DIR}: {e}")
            continue

        for plugin_dir in plugin_dirs:
            main_file = os.path.join(PLUGINS_DIR, plugin_dir, "main.py")
            manifest_file = os.path.join(PLUGINS_DIR, plugin_dir, "manifest.json")

            if not os.path.exists(main_file):
                if debug_log: logger.debug("LOADER", f"Plugin {plugin_dir} has no main.py, skipping.")
                continue

            # --- LAZY LOADING via manifest.json ---
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

                        is_lazy = config.get('plugins', {}).get(tag, {}).get('lazy_load', manifest_data.get("lazy_load", False))

                        if is_lazy:
                            skills_map[tag] = {
                                "description": manifest_data.get("description", ""),
                                "commands": manifest_data.get("commands", {}),
                                "status": "ONLINE (DORMANT)",
                                "example": manifest_data.get("example", ""),
                                "is_class_based": manifest_data.get("is_class_based", True),
                                "is_lazy": True
                            }

                            _lazy_plugins_paths[tag] = os.path.abspath(main_file)

                            from .plugin_state import _lazy_tool_schemas
                            _lazy_tool_schemas[tag] = manifest_data.get("tool_schema", [])

                            if debug_log: logger.debug("LOADER", f"Plugin {plugin_dir} registered (Lazy Load).")
                            continue  # Skip eager import

                except Exception as e:
                    logger.error(f"LOADER: Failed to parse {manifest_file}, falling back to eager load: {e}")

            # --- EAGER LOADING ---
            _load_plugin_from_file(plugin_dir, main_file, PLUGINS_DIR, config, skills_map, debug_log)

    # --- LEGACY plugins_legacy/ support ---
    if os.path.exists("plugins_legacy"):
        legacy_dirs = [d for d in os.listdir("plugins_legacy")
                      if os.path.isdir(os.path.join("plugins_legacy", d))
                      and not d.startswith("__")]

        for legacy_dir in legacy_dirs:
            main_file = os.path.join("plugins_legacy", legacy_dir, "main.py")
            if not os.path.exists(main_file):
                continue
            try:
                spec = importlib.util.spec_from_file_location(f"plugins_legacy.{legacy_dir}.main", main_file)
                if spec is None: continue
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

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
                        continue

                    _loaded_legacy_plugins[tag] = legacy_instance
                    status = legacy_instance.status() if hasattr(legacy_instance, "status") else "ONLINE"
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

    # --- ALSO SCAN old flat .py files for backward compatibility ---
    DEFAULT_PLUGINS_DIR = os.path.join(ZENTRA_DIR, "plugins")
    old_plugins_files = glob.glob(os.path.join(DEFAULT_PLUGINS_DIR, "*.py"))
    for file in old_plugins_files:
        module_name = os.path.basename(file)[:-3]
        if module_name.startswith("__") or module_name.startswith("_"):
            continue
        if module_name in [os.path.basename(p) for p in search_paths]:
            continue
        try:
            spec = importlib.util.spec_from_file_location(module_name, file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if hasattr(module, "info"):
                plugin_info = module.info()
                tag = plugin_info['tag']
                plugin_enabled = config.get('plugins', {}).get(tag, {}).get('enabled', True)
                if not plugin_enabled:
                    continue
                status = module.status() if hasattr(module, "status") else "ONLINE"
                skills_map[tag] = {
                    "description": plugin_info.get('desc') or plugin_info.get('description', ''),
                    "commands": plugin_info.get('comandi') or plugin_info.get('commands', {}),
                    "status": status,
                    "example": plugin_info.get("esempio") or plugin_info.get("example", "")
                }
                if hasattr(module, "config_schema"):
                    _plugin_config_schemas[tag] = module.config_schema()
        except Exception as e:
            logger.error(f"LOADER: Failed to load legacy flat {module_name}: {e}")
            continue

    # --- Write central registry ---
    try:
        with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
            json.dump(skills_map, f, indent=4, ensure_ascii=False)
        if debug_log:
            logger.info(f"REGISTRY: Capabilities registry updated ({len(skills_map)} modules).")
    except Exception as e:
        logger.error(f"REGISTRY: File write error: {e}")

    return skills_map
