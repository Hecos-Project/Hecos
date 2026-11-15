"""

MODULE: Plugin Docs

DESCRIPTION: Generates documentation, UI schemas, and AI function calling schemas.

"""



import os

import json

import importlib.util

import glob

from hecos.core.logging import logger

from hecos.core.i18n import translator



from .module_state import (

    REGISTRY_PATH,

    _loaded_plugins,

    _loaded_legacy_plugins,

    _lazy_plugins_paths,

    _lazy_tool_schemas,

    _lazy_llm_callable

)

from .module_scanner import update_capability_registry



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



def _parse_tool_docstring(docstring):

    if not docstring:
        return "Tool function", {}

    lines = docstring.strip().split('\n')
    description = lines[0].strip()
    params_description = {}

    import re
    for line in lines[1:]:
        match = re.search(r':param\s+(\w+):\s+(.+)', line)
        if match:
            params_description[match.group(1)] = match.group(2).strip()

    return description, params_description


def _sanitize_tool_schema(schema_list):
    """
    Ensures every array-type parameter has an 'items' key.
    Gemini rejects tool declarations that have type=array without items.
    Also creates clean copies to prevent in-place cache mutation.
    """
    import copy
    sanitized = []
    for tool in schema_list:
        tool_copy = copy.deepcopy(tool)
        if "type" not in tool_copy and "function" not in tool_copy:
            tool_copy = {"type": "function", "function": tool_copy.get("function", tool_copy)}
        func = tool_copy.get("function", tool_copy)
        params = func.get("parameters", {})
        props = params.get("properties", {})
        for prop in props.values():
            if prop.get("type") == "array" and "items" not in prop:
                prop["items"] = {"type": "string"}
        sanitized.append(tool_copy)
    return sanitized


def _extract_module_tools(tag, module):
    """Extract JSON function-calling schemas from a loaded plugin instance."""
    import inspect

    extracted = []
    if hasattr(module, "tools"):
        tools_instance = module.tools
        for name, method in inspect.getmembers(tools_instance, predicate=inspect.ismethod):
            if name.startswith('_') or name.startswith('slash_'):
                continue
            if tag == "MCP_BRIDGE" and name in ["get_mcp_schemas", "call_tool"]:
                continue

            description, params_description = _parse_tool_docstring(method.__doc__)
            signature = inspect.signature(method)

            properties = {}
            required = []
            for param_name, param in signature.parameters.items():
                if param_name == 'self':
                    continue
                param_description = params_description.get(param_name, f"Parameter {param_name}")
                properties[param_name] = {
                    "type": "string",
                    "description": param_description
                }
                if param.default == inspect.Parameter.empty:
                    required.append(param_name)

            extracted.append({
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

    if tag == "MCP_BRIDGE" and hasattr(module, "tools") and hasattr(module.tools, "get_mcp_schemas"):
        try:
            mcp_dynamic_schemas = module.tools.get_mcp_schemas()
            if mcp_dynamic_schemas:
                extracted.extend(_sanitize_tool_schema(mcp_dynamic_schemas))
        except Exception as e:
            logger.error(f"DOCS: Failed to fetch dynamic MCP schemas: {e}")

    return extracted


def _apply_docs_overrides(tools_list):
    """Apply runtime Document Maker directive overrides to matching tools in-place."""
    try:
        _dm_cfg_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "hpm", "document_maker", "docs_config.json"
        )
        if not os.path.exists(_dm_cfg_path):
            return
        with open(_dm_cfg_path, "r", encoding="utf-8") as _f:
            _dm_cfg = json.load(_f)

        _override_enabled = _dm_cfg.get("override_enabled", True)
        _override_directive = _dm_cfg.get("override_directive", "").strip()
        if not (_override_enabled and _override_directive):
            return

        _def_tpl_id = _dm_cfg.get("default_template_id", "").strip()
        _extra_tpl_info = ""
        if _def_tpl_id:
            try:
                from hecos.hpm.libraries.templates.store import get_template
                _tpl_data = get_template(_def_tpl_id)
                _tpl_name = _tpl_data.get("name", _def_tpl_id) if _tpl_data else _def_tpl_id
                _extra_tpl_info = (
                    f"\n\nCURRENT CONFIGURED DEFAULT TEMPLATE:\nName: '{_tpl_name}' | ID: '{_def_tpl_id}'. "
                    f"When the user asks for 'default template', 'modello predefinito', or 'il solito documento', "
                    f"use this template (pass template_id='{_def_tpl_id}')."
                )
            except Exception:
                pass

        _full_directive = _override_directive + _extra_tpl_info
        _override_targets = {
            "DOCS__generate_pdf",
            "DOCS__modify_document",
            "DOCS__list_documents",
        }
        for _tool in tools_list:
            _func = _tool.get("function", _tool)
            _tname = _func.get("name", "")
            if _tname in _override_targets:
                curr_desc = _func.get("description", "")
                if _full_directive and _full_directive not in curr_desc:
                    _func["description"] = (curr_desc + " " + _full_directive).strip()
    except Exception:
        pass  # Never crash tool assembly due to override issues


def _build_builtin_system_tool():
    return {
        "type": "function",
        "function": {
            "name": "SYSTEM__describe_module",
            "description": (
                "Returns a detailed capability profile (capability card) for any installed Hecos module or package. "
                "Use this when the user asks 'what can X do?', 'does the webcam plugin have a widget?', "
                "'what commands does the reminder module have?', 'list all LLM tools of calendar', "
                "or any question about a specific module's features, type, or capabilities."
            ),
            "parameters": {
                "type": "object",
                "required": ["module_id"],
                "properties": {
                    "module_id": {
                        "type": "string",
                        "description": (
                            "The ID of the module to describe (e.g. 'webcam', 'calendar', 'reminder', "
                            "'lists', 'weather_pro', 'voice_visualizer', 'quick_links', 'map', "
                            "'image_gen', 'webcam_feed'). Use lowercase with underscores."
                        )
                    }
                }
            }
        }
    }


def _build_builtin_core_author_tool():
    return {
        "type": "function",
        "function": {
            "name": "CORE__get_author",
            "description": (
                "Returns the verified authorship and copyright information for Hecos. "
                "Use this when the user asks 'who made Hecos?', 'who is the author?', "
                "'chi ha creato Hecos?', 'di chi è Hecos?', 'chi è Antonio Meloni?', "
                "'show copyright', 'show author info', or any question about the creator, "
                "ownership, or legal identity of the Hecos system."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "include_address": {
                        "type": "boolean",
                        "description": "If true, includes the registered physical address of the author. Default false."
                    }
                }
            }
        }
    }


def _parse_tool_selection(payload_control):
    """Parse tool_selection_mode ('all'|'custom') and selected_tools wildcards/names."""
    if not isinstance(payload_control, dict):
        return "all", set(), set()

    mode = str(payload_control.get("tool_selection_mode") or "all").strip().lower()
    if mode != "custom":
        return "all", set(), set()

    raw_selected = payload_control.get("selected_tools") or []
    if not isinstance(raw_selected, (list, tuple, set)):
        raw_selected = []

    selected_set = set()
    wildcard_tags = set()
    for item in raw_selected:
        entry = str(item).strip()
        if not entry:
            continue
        if entry.endswith("__*"):
            tag_prefix = entry[:-3].strip()
            if tag_prefix:
                wildcard_tags.add(tag_prefix)
        else:
            selected_set.add(entry)

    return "custom", selected_set, wildcard_tags


def _is_tool_selected(tool_name, tag, mode, selected_set, wildcard_tags):
    if mode != "custom":
        return True
    return (tag in wildcard_tags) or (tool_name in selected_set)


def _ensure_registry_populated():
    if not _loaded_plugins and not _lazy_tool_schemas:
        logger.debug("DOCS", "Memory schemas empty, triggering capability rescan...")
        update_capability_registry(debug_log=False)


def _resolve_plugins_cfg(config=None):
    if isinstance(config, dict) and "plugins" in config:
        return config.get("plugins") or {}
    try:
        from hecos.app.config import ConfigManager as _CM
        return _CM().config.get("plugins", {})
    except Exception:
        return {}


def _load_registry_metadata_by_tag():
    """Load module metadata keyed by uppercase plugin tag from capabilities.json."""
    by_tag = {}
    try:
        if not os.path.exists(REGISTRY_PATH):
            return by_tag
        with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        for mod in data.get("modules", []) or []:
            mod_id = str(mod.get("id") or "").strip()
            tag = mod_id.upper() if mod_id else ""
            if tag:
                by_tag[tag] = mod
    except Exception:
        pass
    return by_tag


def get_available_tools_catalog(config=None):
    """
    Build a live, dynamic catalog of all currently installed/active LLM-callable
    modules and their tools (including dormant lazy plugins via _lazy_tool_schemas).
    Used by Quick Config (Soul Forge) to populate granular per-chat/per-preset tool selectors.
    """
    _ensure_registry_populated()
    _plugins_cfg = _resolve_plugins_cfg(config)
    registry_by_tag = _load_registry_metadata_by_tag()

    modules_out = []

    def _finalize_module_entry(tag, schemas, is_lazy, loaded_in_ram, source_override=None, name_override=None, desc_override=None):
        if not schemas:
            return
        _apply_docs_overrides(schemas)

        reg = registry_by_tag.get(tag, {})
        mod_id = reg.get("id") or tag.lower()
        mod_name = name_override or reg.get("name") or mod_id.replace("_", " ").title()
        mod_desc = desc_override or reg.get("description") or ""
        mod_source = source_override or reg.get("source") or ("hpm" if tag in _lazy_plugins_paths else "core")

        tools_meta = []
        mod_chars = 0
        for tool in schemas:
            func = tool.get("function", tool)
            fname = func.get("name", "")
            if not fname:
                continue
            fdesc = func.get("description", "")
            params_obj = func.get("parameters", {}) or {}
            props = params_obj.get("properties", {}) or {}
            required = params_obj.get("required", []) or []

            t_chars = len(json.dumps(tool, ensure_ascii=False))
            mod_chars += t_chars
            short_method = fname.split("__", 1)[1] if "__" in fname else fname
            tools_meta.append({
                "name": fname,
                "method": short_method,
                "description": fdesc,
                "params": list(props.keys()),
                "required": list(required),
                "chars": t_chars,
                "est_tokens": max(1, round(t_chars / 4)),
            })

        if not tools_meta:
            return

        tools_meta.sort(key=lambda t: t["name"])
        modules_out.append({
            "tag": tag,
            "id": mod_id,
            "name": mod_name,
            "description": mod_desc,
            "source": mod_source,
            "is_lazy": bool(is_lazy),
            "loaded_in_ram": bool(loaded_in_ram),
            "tool_count": len(tools_meta),
            "chars": mod_chars,
            "est_tokens": max(1, round(mod_chars / 4)),
            "tools": tools_meta,
        })

    # 1. Currently loaded plugins in RAM (core + awakened lazy plugins)
    seen_tags = set()
    for tag, module in _loaded_plugins.items():
        if not _plugins_cfg.get(tag, {}).get("llm_callable", True):
            continue
        seen_tags.add(tag)
        schemas = _sanitize_tool_schema(_extract_module_tools(tag, module))
        reg = registry_by_tag.get(tag, {})
        is_lazy = bool(reg.get("lazy_load", False) or tag in _lazy_plugins_paths)
        _finalize_module_entry(tag, schemas, is_lazy=is_lazy, loaded_in_ram=True)

    # 2. Dormant lazy plugins (schemas cached in _lazy_tool_schemas during scan)
    for tag, lazy_schemas in _lazy_tool_schemas.items():
        if tag in seen_tags:
            continue
        if not _lazy_llm_callable.get(tag, True):
            continue
        if not _plugins_cfg.get(tag, {}).get("llm_callable", True):
            continue
        schemas = _sanitize_tool_schema(lazy_schemas or [])
        _finalize_module_entry(tag, schemas, is_lazy=True, loaded_in_ram=False)

    # 3. Built-in SYSTEM inspection tool
    _finalize_module_entry(
        "SYSTEM",
        [_build_builtin_system_tool()],
        is_lazy=False,
        loaded_in_ram=True,
        source_override="builtin",
        name_override="System Inspection",
        desc_override="Inspect installed Hecos modules and capability cards."
    )

    modules_out.sort(key=lambda m: (0 if not m["is_lazy"] else 1, m["tag"]))
    total_tools = sum(m["tool_count"] for m in modules_out)
    total_chars = sum(m["chars"] for m in modules_out)

    return {
        "modules": modules_out,
        "total_modules": len(modules_out),
        "total_tools": total_tools,
        "total_chars": total_chars,
        "total_est_tokens": max(1, round(total_chars / 4)) if total_chars else 0,
    }


def get_tools_schema(payload_control=None, config=None):
    """
    Scans loaded class-based plugins (and explicitly selected lazy plugins in custom mode)
    and generates a list of tools in the JSON Schema format expected by LiteLLM / OpenAI.
    """
    _ensure_registry_populated()
    _plugins_cfg = _resolve_plugins_cfg(config)
    mode, selected_set, wildcard_tags = _parse_tool_selection(payload_control)

    if mode == "custom" and not selected_set and not wildcard_tags:
        return None

    tools_list = []

    # 1. Loaded plugins in RAM
    for tag, module in _loaded_plugins.items():
        if not _plugins_cfg.get(tag, {}).get("llm_callable", True):
            continue

        extracted = _sanitize_tool_schema(_extract_module_tools(tag, module))
        if mode == "custom":
            for tool in extracted:
                fname = tool.get("function", {}).get("name", "")
                if _is_tool_selected(fname, tag, mode, selected_set, wildcard_tags):
                    tools_list.append(tool)
        else:
            tools_list.extend(extracted)

    # 2. Lazy plugins:
    # In 'all' mode, dormant lazy plugins stay OUT of the payload by design.
    # In 'custom' mode, if a user/preset explicitly checked a lazy module or tool for this chat/preset,
    # expose its cached schema (tool_invoker will JIT-load it when invoked).
    if mode == "custom":
        for tag, lazy_schemas in _lazy_tool_schemas.items():
            if tag in _loaded_plugins:
                continue
            if not _lazy_llm_callable.get(tag, True):
                continue
            if not _plugins_cfg.get(tag, {}).get("llm_callable", True):
                continue
            for tool in _sanitize_tool_schema(lazy_schemas or []):
                fname = tool.get("function", {}).get("name", "")
                if _is_tool_selected(fname, tag, mode, selected_set, wildcard_tags):
                    tools_list.append(tool)

    # 3. Built-in SYSTEM inspection tool
    if _is_tool_selected("SYSTEM__describe_module", "SYSTEM", mode, selected_set, wildcard_tags):
        tools_list.append(_build_builtin_system_tool())

    # If custom mode matched zero installed/valid tools (e.g. preset referenced an uninstalled package),
    # return None safely instead of forcing tool mode with only CORE__get_author.
    if mode == "custom" and not tools_list:
        return None

    # --- RUNTIME AI BEHAVIOR OVERRIDES (from Document Maker config) ---
    _apply_docs_overrides(tools_list)

    # --- BUILT-IN CORE IDENTITY TOOL (present whenever tools payload is non-empty) ---
    tools_list.append(_build_builtin_core_author_tool())

    return tools_list if tools_list else None




