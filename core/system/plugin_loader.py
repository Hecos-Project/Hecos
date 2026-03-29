"""
MODULE: Plugin Loader & Capability Registry - Zentra Core
DESCRIPTION: Handles dynamic scanning of plugins (now in subfolders)
and creation of the central JSON registry. Also supports gathering
configuration schemas for plugins.
"""

import importlib.util
import os
import glob
import json
from core.logging import logger
from core.i18n import translator

REGISTRY_PATH = "core/registry.json"

# Stores configuration schemas collected from plugins
_plugin_config_schemas = {}

# Active plugins (Native and Legacy)
_loaded_plugins = {}          # tag -> module (for JSON Calling / old single plugins)
_loaded_legacy_plugins = {}   # tag -> instance of LegacyPlugin class

def get_active_tags():
    """Returns a list of all currently active plugin tags."""
    return list(_loaded_plugins.keys()) + list(_loaded_legacy_plugins.keys())

def get_plugin_module(tag, legacy=False):
    """Returns the plugin module if active, otherwise None."""
    if legacy:
        return _loaded_legacy_plugins.get(tag)
    return _loaded_plugins.get(tag)

def update_capability_registry(config=None, debug_log=True):
    """
    Scans the plugins directory, queries the info() manifest, and
    generates a centralized JSON file with all active abilities.
    If config is passed, it uses it to check the 'enabled' flag.
    """
    global _plugin_config_schemas, _loaded_plugins, _loaded_legacy_plugins
    _plugin_config_schemas.clear()
    _loaded_plugins.clear()
    _loaded_legacy_plugins.clear()
    skills_map = {}

    # If we don't have config, load it (for backward compatibility)
    if config is None:
        from app.config import ConfigManager
        config = ConfigManager().config

    # Search in the new structure (subfolders with main.py)
    plugin_dirs = [d for d in os.listdir("plugins")
                  if os.path.isdir(os.path.join("plugins", d))
                  and not d.startswith("__")
                  and d != "plugins_disabled"]

    for plugin_dir in plugin_dirs:
        main_file = os.path.join("plugins", plugin_dir, "main.py")
        if not os.path.exists(main_file):
            logger.debug("LOADER", f"Plugin {plugin_dir} without main.py, ignored")
            continue

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
                    "example": plugin_info.get("esempio") or plugin_info.get("example", "")
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
    if os.path.exists("plugins_legacy"):
        legacy_dirs = [d for d in os.listdir("plugins_legacy")
                      if os.path.isdir(os.path.join("plugins_legacy", d))
                      and not d.startswith("__")]

        for legacy_dir in legacy_dirs:
            main_file = os.path.join("plugins_legacy", legacy_dir, "main.py")
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
    old_plugins_files = glob.glob(os.path.join("plugins", "*.py"))
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

    # Centralized registry writing
    try:
        with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
            json.dump(skills_map, f, indent=4, ensure_ascii=False)
        if debug_log:
            logger.info(f"REGISTRY: Capabilities registry updated ({len(skills_map)} modules).")
    except Exception as e:
        logger.error(f"REGISTRY: File write error: {e}")

    return skills_map

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

def get_formatted_capabilities():
    """Returns a readable string for the terminal."""
    if not os.path.exists(REGISTRY_PATH):
        update_capability_registry()

    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    result_string = f"\n=== {translator.t('help_registry_title')} ===\n"
    for tag, info in data.items():
        result_string += f"\n[MODULE: {tag}] - {translator.t('system_status', status=info['status'])}\n"
        result_string += f"{translator.t('help_role')} {info['description']}\n"
        for command, explanation in info['commands'].items():
            result_string += f"  • {tag}:{command} --> {explanation}\n"
    return result_string

def generate_dynamic_guide():
    """
    Scans all plugin folders (active and disabled) to get
    necessary metadata to build the user guide (F1).
    Returns a list of dictionaries with module details.
    """
    guide = []

    def scan_directory(base_path, forced_status=None):
        if not os.path.exists(base_path):
            return

        plugin_dirs = [d for d in os.listdir(base_path)
                       if os.path.isdir(os.path.join(base_path, d))
                       and not d.startswith("__")
                       and d != "plugins_disabled"]

        for plugin_dir in plugin_dirs:
            main_file = os.path.join(base_path, plugin_dir, "main.py")
            if not os.path.exists(main_file):
                continue
            try:
                spec = importlib.util.spec_from_file_location(
                    f"guide_{os.path.basename(base_path)}_{plugin_dir}",
                    main_file
                )
                if spec is None:
                    continue
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                if hasattr(module, "info"):
                    plugin_info = module.info()
                    effective_status = forced_status if forced_status else (module.status() if hasattr(module, "status") else translator.t("online"))

                    guide.append({
                        "tag": plugin_info['tag'],
                        "description": plugin_info.get('desc', 'No description.'),
                        "commands": plugin_info.get('comandi', {}),
                        "status": effective_status,
                        "example": plugin_info.get("esempio", "")
                    })
            except Exception as e:
                logger.error(f"GUIDE LOADER: Failed for {plugin_dir}: {e}")

    # 1. Scan active plugins
    scan_directory("plugins")

    # 2. Scan disabled plugins (force OFFLINE status)
    scan_directory(os.path.join("plugins", "plugins_disabled"), forced_status=translator.t("offline"))

    # 3. Scan old plugins in root "plugins" for compatibility
    old_files = glob.glob(os.path.join("plugins", "*.py"))
    for file in old_files:
        module_name = os.path.basename(file)[:-3]
        if module_name.startswith("__") or module_name.startswith("_"):
            continue
        try:
            spec = importlib.util.spec_from_file_location(f"guide_{module_name}", file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if hasattr(module, "tools"):
                tools_instance = module.tools
                effective_status = getattr(tools_instance, "status", translator.t("online"))
                import inspect
                commands = {}
                for name, method in inspect.getmembers(tools_instance, predicate=inspect.ismethod):
                    if not name.startswith('_'):
                        doc = method.__doc__
                        commands[name] = doc.strip().split('\n')[0] if doc else "Method"
                if not any(g['tag'] == tools_instance.tag for g in guide):
                    guide.append({
                        "tag": tools_instance.tag,
                        "description": getattr(tools_instance, "desc", "No description."),
                        "commands": commands,
                        "status": effective_status,
                        "example": ""
                    })
            elif hasattr(module, "info"):
                plugin_info = module.info()
                effective_status = module.status() if hasattr(module, "status") else translator.t("online")
                # Avoid duplicates if present in folder
                if not any(g['tag'] == plugin_info['tag'] for g in guide):
                    guide.append({
                        "tag": plugin_info['tag'],
                        "description": plugin_info.get('desc', 'No description.'),
                        "commands": plugin_info.get('comandi', {}),
                        "status": effective_status,
                        "example": plugin_info.get("esempio", "")
                    })
        except:
            pass

    # Sort by alphabetical tag
    guide.sort(key=lambda x: x['tag'])
    return guide

def get_tools_schema():
    """
    Scans loaded class-based plugins and generates a list of tools
    in the JSON Schema format expected by LiteLLM / OpenAI for Function Calling.
    """
    import inspect
    import re

    tools_list = []

    def _parse_docstring(docstring):
        if not docstring: return "Tool function", {}
        lines = docstring.strip().split('\n')
        description = lines[0].strip()
        params_description = {}
        for line in lines[1:]:
            match = re.search(r':param\s+(\w+):\s+(.+)', line)
            if match:
                params_description[match.group(1)] = match.group(2).strip()
        return description, params_description

    for tag, module in _loaded_plugins.items():
        if hasattr(module, "tools"):
            tools_instance = module.tools
            for name, method in inspect.getmembers(tools_instance, predicate=inspect.ismethod):
                if name.startswith('_'):
                    continue

                description, params_description = _parse_docstring(method.__doc__)
                signature = inspect.signature(method)

                properties = {}
                required = []

                for param_name, param in signature.parameters.items():
                    if param_name == 'self':
                        continue

                    # Set everything to string for simplicity, based on docstring
                    param_description = params_description.get(param_name, f"Parameter {param_name}")
                    properties[param_name] = {
                        "type": "string",
                        "description": param_description
                    }
                    if param.default == inspect.Parameter.empty:
                        required.append(param_name)

                tools_list.append({
                    "type": "function",
                    "function": {
                        "name": f"{tag}__{name}",
                        "description": description,
                        "parameters": {
                            "type": "object",
                            "properties": properties,
                            "required": required
                        }
                    }
                })

    return tools_list if tools_list else None

def get_legacy_schema():
    """
    Returns a formatted string with the list of available TAGS.
    Supports both legacy functional plugins and new class-based plugins.
    """
    if not _loaded_legacy_plugins and not _loaded_plugins:
        return ""

    result_string = "### ACTIVE SKILLS AND COMMANDS (TAG MODE) ###\n"
    result_string += "- You can trigger actions by writing text tags in the format [TAG: command:parameters].\n"
    
    # 1. Legacy Plugins (SYSTEM, WEB)
    for tag, instance in _loaded_legacy_plugins.items():
        info = instance.info()
        commands = info.get("comandi", {})
        result_string += f"\n[MODULE: {tag}]\n"
        for command, desc in commands.items():
            result_string += f"  - [{tag}: {command}] : {desc}\n"

    # 2. Native Class-based Plugins (IMAGE_GEN, DASHBOARD, etc.)
    import inspect
    for tag, module in _loaded_plugins.items():
        if hasattr(module, "tools"):
            result_string += f"\n[MODULE: {tag}]\n"
            tools_instance = module.tools
            for name, method in inspect.getmembers(tools_instance, predicate=inspect.ismethod):
                if name.startswith('_'): continue
                
                # Get description from docstring
                doc = method.__doc__ or "Execute command"
                desc = doc.strip().split('\n')[0]
                
                # Get parameters
                sig = inspect.signature(method)
                params = [p for p in sig.parameters.keys() if p != 'self']
                param_str = ": " + ",".join(params) if params else ""
                
                result_string += f"  - [{tag}: {name}{param_str}] : {desc}\n"

    result_string += "\nATTENTION: Tags must be exactly in [TAG: command] format to be executed.\n"
    return result_string

