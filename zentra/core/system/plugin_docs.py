"""
MODULE: Plugin Docs
DESCRIPTION: Generates documentation, UI schemas, and AI function calling schemas.
"""

import os
import json
import importlib.util
import glob
from zentra.core.logging import logger
from zentra.core.i18n import translator

from .plugin_state import (
    REGISTRY_PATH,
    _loaded_plugins,
    _loaded_legacy_plugins,
    _lazy_plugins_paths,
    _lazy_tool_schemas
)
from .plugin_scanner import update_capability_registry

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

    import os
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    plugins_dir = os.path.join(BASE_DIR, "plugins")
    disabled_dir = os.path.join(plugins_dir, "plugins_disabled")

    # 1. Scan active plugins
    scan_directory(plugins_dir)

    # 2. Scan disabled plugins (force OFFLINE status)
    scan_directory(disabled_dir, forced_status=translator.t("offline"))

    # 3. Scan old plugins in root "plugins" for compatibility
    old_files = glob.glob(os.path.join(plugins_dir, "*.py"))
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
                        "example": getattr(tools_instance, "esempio", "")
                    })
            elif hasattr(module, "info"):
                plugin_info = module.info()
                effective_status = module.status() if hasattr(module, "status") else translator.t("online")
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

    # CRITICAL: Ensure _lazy_tool_schemas is populated if this is a fresh process
    if not _loaded_plugins and not _lazy_tool_schemas:
        logger.debug("DOCS", "Memory schemas empty, triggering capability rescan...")
        update_capability_registry(debug_log=False)

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
                        
                # Ensure we don't expose internal MCP bridge handlers directly to the AI
                if tag == "MCP_BRIDGE" and name in ["get_mcp_schemas", "call_tool"]:
                    continue

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
                
        # --- NEW: Inject flattened dynamic MCP Schemas directly from the bridge ---
        if tag == "MCP_BRIDGE" and hasattr(module, "tools") and hasattr(module.tools, "get_mcp_schemas"):
            try:
                mcp_dynamic_schemas = module.tools.get_mcp_schemas()
                if mcp_dynamic_schemas:
                    tools_list.extend(mcp_dynamic_schemas)
            except Exception as e:
                logger.error(f"DOCS: Failed to fetch dynamic MCP schemas: {e}")

    # --- ADD LAZY PLUGINS SCHEMAS ---
    for tag, schema_list in _lazy_tool_schemas.items():
        if tag not in _loaded_plugins: # Don't duplicate if already awakened
            tools_list.extend(schema_list)

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

    # 3. Dormant Lazy Plugins (Tag info from registry)
    if os.path.exists(REGISTRY_PATH):
        try:
            with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
                reg = json.load(f)
            for tag, info in reg.items():
                if tag not in _loaded_plugins and tag not in _loaded_legacy_plugins:
                    is_lazy = tag in _lazy_plugins_paths
                    if is_lazy or "DORMANT" in info.get("status", ""):
                        result_string += f"\n[MODULE: {tag}] (Dormant)\n"
                        # Improve documentation by showing parameters if they exist in _lazy_tool_schemas
                        lazy_commands = info.get("commands", {})
                        
                        # Peek into tool_schema for param names
                        param_map = {}
                        if tag in _lazy_tool_schemas:
                            for schema in _lazy_tool_schemas[tag]:
                                func_name = schema.get("function", {}).get("name", "")
                                if "__" in func_name:
                                    _, actual_cmd = func_name.split("__", 1)
                                    props = schema.get("function", {}).get("parameters", {}).get("properties", {})
                                    if props:
                                        param_map[actual_cmd] = list(props.keys())

                        for cmd, dsc in lazy_commands.items():
                            p_list = param_map.get(cmd, [])
                            p_str = ": " + ",".join(p_list) if p_list else ""
                            result_string += f"  - [{tag}: {cmd}{p_str}] : {dsc}\n"
        except: pass

    result_string += "\nATTENTION: Tags must be exactly in [TAG: command] format to be executed.\n"
    return result_string
