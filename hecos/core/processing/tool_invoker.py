"""
hecos/core/processing/tool_invoker.py
Execution adapters for Hecos tools:
- Builtin SYSTEM__ and CORE__ tools
- Slash commands via CommandExecutor
- External MCP servers via MCP_BRIDGE
- Native Plugin .tools classes (with argument parsing and signature reflection)
- Legacy OOP plugins (process_tag / elabora_tag)
- Plugin .execute() entry points
- Direct engine methods
- Missing plugin fallback handling
"""

import inspect
import json
import re
from typing import Any, Dict, Optional, Tuple

from hecos.core.logging import logger
from hecos.core.i18n import translator
from hecos.core.processing.tool_limits import update_image_turn_counters


def execute_system_tool(
    method_name: str,
    args: Any,
    call_id: str,
    current_config: dict,
) -> Optional[str]:
    """Dispatcher for built-in SYSTEM__ LLM tools."""
    if method_name == "describe_module":
        module_id = args.get("module_id", "") if isinstance(args, dict) else str(args).strip()
        if not module_id:
            return "Error: module_id parameter is required."
        try:
            from hecos.core.system.capability_inspector import build_card
            introspect = (
                current_config.get("hpm", {}).get("auto_introspect", False)
                if isinstance(current_config, dict)
                else False
            )
            card = build_card(module_id.strip().lower(), introspect=introspect)
            if card is None:
                return (
                    f"Module '{module_id}' is not installed or not found. "
                    f"Known packages: webcam, webcam_feed, calendar, reminder, lists, "
                    f"weather_pro, map, image_gen, voice_visualizer, quick_links."
                )
            return (
                f"Module: {card.name} (id={card.id}) v{card.version}\n"
                f"Type: {card.type} | Author: {card.author}\n"
                f"Description: {card.description}\n"
                f"LLM Tools ({len(card.llm_tools)}): {', '.join(card.llm_tools) or 'none'}\n"
                f"Direct Commands (/): {', '.join(card.slash_commands) or 'none'}\n"
                f"Has Widget: {card.has_widget} | Config Panel: {card.has_config_panel} | "
                f"API Routes: {card.has_api_routes} | System Calls: {card.has_system_calls}\n"
                + (f"Syscall notes: {card.syscall_notes}\n" if card.syscall_notes else "")
                + (f"Notes: {card.notes}" if card.notes else "")
            )
        except Exception as e:
            logger.error(f"[SYSTEM__describe_module] Error: {e}")
            return f"Error retrieving capability card for '{module_id}': {e}"

    logger.warning(f"[PROCESSOR] Unknown SYSTEM built-in tool: '{method_name}'")
    return None


def execute_core_tool(
    method_name: str,
    args: Any,
    call_id: str,
) -> Optional[str]:
    """Dispatcher for built-in CORE__ LLM tools."""
    if method_name == "get_author":
        include_address = args.get("include_address", False) if isinstance(args, dict) else False
        try:
            from hecos.core.identity import get_author_card
            return get_author_card(include_address=include_address)
        except ImportError:
            return "Error: core.identity module not found."
        except Exception as e:
            logger.error(f"[CORE__get_author] Error: {e}")
            return f"Error retrieving authorship info: {e}"

    logger.warning(f"[PROCESSOR] Unknown CORE built-in tool: '{method_name}'")
    return None


def execute_slash_command(
    raw_command: Any,
    call_id: str,
    current_config: dict,
    is_image_call: bool,
    image_limit: int,
    images_already_done: int,
    sm: Any = None,
) -> Tuple[Dict[str, Any], int]:
    """Executes a direct / command through the command executor."""
    from hecos.core.commands.executor import get_executor
    executor = get_executor()
    try:
        res = executor.execute(
            raw_input=raw_command,
            config=current_config,
            config_manager=None,
            current_user_role="admin",
            current_user_id="admin",
            page_context="agent_internal",
        )
        if res.get("ok"):
            output_val = res.get("output", "")
        else:
            err_detail = res.get("error") or res.get("output") or "Unknown command error"
            output_val = f"Error: {err_detail}"
    except Exception as e:
        logger.error(f"[PROCESSOR] Error executing slash command: {e}")
        output_val = f"Error: {e}"

    new_done = update_image_turn_counters(
        output_val, is_image_call, image_limit, images_already_done, sm
    )
    return {"id": call_id, "output": output_val, "tag": "SLASH_COMMAND"}, new_done


def execute_mcp_tool(
    module_to_call: str,
    method_name: Optional[str],
    action_or_args: Any,
    call_id: str,
) -> Optional[Dict[str, Any]]:
    """Routes external tool calls to the MCP_BRIDGE if a matching server is found."""
    from hecos.core.system import module_loader

    mcp_module = module_loader.get_plugin_module("MCP_BRIDGE", legacy=False)
    mcp_bridge_instance = getattr(mcp_module, "bridge_instance", None) if mcp_module else None

    if not mcp_bridge_instance or not hasattr(mcp_bridge_instance, "proxies"):
        return None

    target_server = (
        module_to_call[4:].lower()
        if module_to_call.upper().startswith("MCP_")
        else module_to_call.lower()
    )

    resolved_server = None
    for p_name in mcp_bridge_instance.proxies.keys():
        if p_name.lower() == target_server:
            resolved_server = p_name
            break

    if not resolved_server:
        return None

    logger.info(f"[SYSTEM] Routing external tool {method_name} to MCP Provider: {resolved_server}")
    try:
        args_dict = action_or_args if isinstance(action_or_args, dict) else {}
        result = mcp_bridge_instance.execute_mcp_tool(resolved_server, method_name, **args_dict)
        if result:
            logger.info(f"[OUTPUT MCP_{resolved_server.upper()}]:\n{result}")
            return {"id": call_id, "output": str(result), "tag": f"MCP_{resolved_server.upper()}"}
    except Exception as e:
        logger.error(f"[PROCESSOR] MCP Tool error ({resolved_server}:{method_name}): {e}")
        return {"id": call_id, "output": f"Error: {e}", "tag": f"MCP_{resolved_server.upper()}"}

    return None


def parse_call_kwargs(raw_call_args: str) -> Any:
    """
    Parses Python/JSON-style call arguments into a kwargs dict (or fallback scalar/empty dict).
    Supports multiline triple-quoted strings, AST literals, escaped quotes, bare enum words, ints, floats, and bools.
    """
    raw = (raw_call_args or "").strip()
    if not raw:
        return {}
    if raw.startswith("{") and raw.endswith("}"):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass

    # Primary pass: safe AST parsing of keyword arguments (handles triple-quoted multiline strings cleanly)
    try:
        import ast
        expr = ast.parse(f"_call({raw})", mode="eval")
        if isinstance(expr.body, ast.Call) and expr.body.keywords and not expr.body.args:
            ast_kwargs: Dict[str, Any] = {}
            for kw in expr.body.keywords:
                if kw.arg is not None:
                    ast_kwargs[kw.arg] = ast.literal_eval(kw.value)
            if ast_kwargs:
                return ast_kwargs
    except Exception:
        pass

    parsed_kwargs: Dict[str, Any] = {}
    kw_pat = re.compile(
        r'(?:^|[\s,]+)([a-zA-Z0-9_]+)\s*=\s*(?:"""([\s\S]*?)"""|\'\'\'([\s\S]*?)\'\'\'|"((?:\\.|[^"])*)"|\'((?:\\.|[^\'])*)\'|([^,\)\s]+))'
    )
    for m in kw_pat.finditer(raw):
        key = m.group(1)
        if m.group(2) is not None:
            val: Any = m.group(2)
        elif m.group(3) is not None:
            val = m.group(3)
        elif m.group(4) is not None:
            val = m.group(4).replace('\\"', '"').replace('\\n', '\n')
        elif m.group(5) is not None:
            val = m.group(5).replace("\\'", "'").replace('\\n', '\n')
        else:
            bare = (m.group(6) or "").strip()
            low = bare.lower()
            if re.fullmatch(r'-?\d+', bare):
                val = int(bare)
            elif re.fullmatch(r'-?\d+\.\d+', bare):
                val = float(bare)
            elif low == "true":
                val = True
            elif low == "false":
                val = False
            elif low in ("none", "null"):
                val = None
            else:
                val = bare
        parsed_kwargs[key] = val

    if parsed_kwargs:
        return parsed_kwargs
    return raw.strip('"\'')


def resolve_native_tools_method_and_args(
    plugin_tools_obj: Any,
    module_to_call: str,
    method_name: Optional[str],
    action_or_args: Any,
) -> Tuple[Optional[str], Any]:
    """
    Parses string-based tool calls into concrete method names and argument dicts/values
    for plugins using the modern `.tools` interface.
    """
    actual_method_name = method_name
    actual_args = action_or_args

    # Normalize raw string args even when method_name was already extracted (e.g. MODULE__method(k=v))
    if actual_method_name and isinstance(action_or_args, str):
        parsed = parse_call_kwargs(action_or_args)
        return actual_method_name, parsed

    if not actual_method_name and isinstance(action_or_args, str):
        clean_str = action_or_args.strip()

        # 1. Match method(args...) syntax e.g. web_search(query="...", engine="SearXNG")
        call_match = re.match(r'^(?:[A-Za-z0-9_]+__)?([a-zA-Z_][a-zA-Z0-9_]*)\s*\((.*)\)$', clean_str, re.DOTALL)
        colon_match = re.match(r'^(?:[A-Za-z0-9_]+__)?([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*(.*)$', clean_str, re.DOTALL)
        space_match = re.match(r'^(?:[A-Za-z0-9_]+__)?([a-zA-Z_][a-zA-Z0-9_]*)(?:\s+(.*))?$', clean_str, re.DOTALL)

        if call_match and hasattr(plugin_tools_obj, call_match.group(1).strip()):
            actual_method_name = call_match.group(1).strip()
            actual_args = parse_call_kwargs(call_match.group(2).strip())

        # 2. Match method: arg syntax ONLY when colon immediately follows identifier
        elif colon_match and hasattr(plugin_tools_obj, colon_match.group(1).strip()):
            actual_method_name = colon_match.group(1).strip()
            m_args = colon_match.group(2).strip()
            actual_args = {
                "query": m_args,
                "prompt": m_args,
                "html_content": m_args,
            }

        # 3. Match bare method or "method key=val ..." / "method {json}" syntax
        elif space_match and hasattr(plugin_tools_obj, space_match.group(1).strip()):
            actual_method_name = space_match.group(1).strip()
            rest = (space_match.group(2) or "").strip()
            if not rest:
                actual_args = {}
            elif rest.startswith("{") and rest.endswith("}"):
                try:
                    actual_args = json.loads(rest)
                except Exception:
                    actual_args = parse_call_kwargs(rest)
            else:
                actual_args = parse_call_kwargs(rest)

        # 3. Default method fallback for IMAGE_GEN / DOCS when called as [IMAGE_GEN: prompt] or [DOCS: html]
        if not actual_method_name:
            if module_to_call.upper() == "IMAGE_GEN" and hasattr(plugin_tools_obj, "generate_image"):
                actual_method_name = "generate_image"
                actual_args = {"prompt": clean_str}
            elif module_to_call.upper() == "DOCS" and hasattr(plugin_tools_obj, "generate_pdf"):
                actual_method_name = "generate_pdf"
                if clean_str.startswith("{") and clean_str.endswith("}"):
                    try:
                        actual_args = json.loads(clean_str)
                    except Exception:
                        actual_args = {"html_content": clean_str}
                else:
                    actual_args = {"html_content": clean_str}

    return actual_method_name, actual_args


def execute_plugin_tool(
    plugin_obj: Any,
    is_legacy_oop: bool,
    module_to_call: str,
    method_name: Optional[str],
    action_or_args: Any,
    call_id: str,
    is_image_call: bool,
    image_limit: int,
    images_already_done: int,
    sm: Any = None,
) -> Tuple[Dict[str, Any], Optional[str], int]:
    """
    Executes a tool on an instantiated plugin module.
    Handles legacy OOP, .tools class, .execute() function, or direct method call.
    """
    mod_tag = module_to_call.upper()
    resolved_method = method_name
    output_val = ""

    # Strategy 1: Legacy OOP (process_tag / elabora_tag)
    if is_legacy_oop and (hasattr(plugin_obj, "process_tag") or hasattr(plugin_obj, "elabora_tag")):
        method_to_call = "process_tag" if hasattr(plugin_obj, "process_tag") else "elabora_tag"
        logger.info(f"[SYSTEM] {translator.t('executing_module', module=mod_tag)}")
        try:
            exec_method = getattr(plugin_obj, method_to_call)
            result = exec_method(action_or_args)
            if result:
                logger.info(f"[OUTPUT {mod_tag}]:\n{result}")
                output_val = str(result)
        except Exception as e:
            logger.error(f"[PROCESSOR] Legacy OOP error: {e}")
            output_val = f"Error: {e}"

    # Strategy 2: Modern .tools class
    elif hasattr(plugin_obj, "tools"):
        actual_method, actual_args = resolve_native_tools_method_and_args(
            plugin_obj.tools, module_to_call, method_name, action_or_args
        )
        resolved_method = actual_method

        if actual_method:
            logger.info(f"[SYSTEM] {translator.t('executing_module', module=mod_tag)}")
            try:
                method = getattr(plugin_obj.tools, actual_method)
                if isinstance(actual_args, dict):
                    sig = inspect.signature(method)
                    valid_kwargs = {k: v for k, v in actual_args.items() if k in sig.parameters}
                    if not valid_kwargs and len(sig.parameters) >= 1 and actual_args:
                        first_param = [p for p in sig.parameters.keys() if p != 'self'][0]
                        valid_kwargs = {first_param: list(actual_args.values())[0]}
                    result = method(**valid_kwargs)
                else:
                    result = method(actual_args)
                if result:
                    logger.info(f"[OUTPUT {mod_tag}]:\n{result}")
                    output_val = str(result)
            except Exception as e:
                logger.error(f"[PROCESSOR] Tool error ({actual_method}): {e}")
                output_val = f"Error: {e}"

    # Strategy 3: Function .execute()
    elif hasattr(plugin_obj, "execute") and not method_name:
        logger.info(f"[SYSTEM] {translator.t('executing_module', module=mod_tag)}")
        try:
            result = plugin_obj.execute(action_or_args)
            if result:
                logger.info(f"[OUTPUT {mod_tag}]: {result}")
                output_val = str(result)
        except Exception as e:
            logger.error(f"[PROCESSOR] Old Plugin error: {e}")
            output_val = f"Error: {e}"

    # Strategy 4: Direct method on plugin or get_plugin()
    elif method_name:
        engine_target = getattr(plugin_obj, "get_plugin", lambda: plugin_obj)()
        if hasattr(engine_target, method_name):
            logger.info(f"[SYSTEM] {translator.t('executing_module', module=mod_tag)} → {method_name}")
            try:
                method = getattr(engine_target, method_name)
                result = (
                    method(**action_or_args)
                    if isinstance(action_or_args, dict)
                    else method(action_or_args)
                )
                if result:
                    logger.info(f"[OUTPUT {mod_tag}]:\n{result}")
                    output_val = str(result)
            except Exception as e:
                logger.error(f"[PROCESSOR] Direct method error ({module_to_call}.{method_name}): {e}")
                output_val = f"Error: {e}"

    new_done = update_image_turn_counters(
        output_val, is_image_call, image_limit, images_already_done, sm
    )
    try:
        args_sig = (
            json.dumps(action_or_args, ensure_ascii=False, sort_keys=True, default=str)[:240]
            if isinstance(action_or_args, dict)
            else str(action_or_args or "")[:240]
        )
    except Exception:
        args_sig = ""
    return {
        "id": call_id,
        "output": output_val,
        "tag": mod_tag,
        "action": resolved_method or method_name or "",
        "args_sig": args_sig,
    }, resolved_method, new_done


def build_missing_plugin_result(
    module_to_call: str,
    call_id: str,
    is_image_call: bool,
    image_limit: int,
    images_already_done: int,
    sm: Any = None,
) -> Tuple[Dict[str, Any], int]:
    """Builds standard missing plugin diagnostic response."""
    mod_upper = module_to_call.upper()
    logger.warning(f"[PROCESSOR] Requested plugin '{mod_upper}' is NOT installed or not active.")

    if mod_upper == "IMAGE_GEN":
        missing_out = (
            "[[IGEN_ALERT]]\n"
            "⚠️ **Plugin Image Generation (`image_gen`) is not installed or active.**\n"
            "To generate photos or images, install or enable the **Image Generation** package from **Packages / Store (HPM)**.\n"
            "[[/IGEN_ALERT]]\n"
            "[SYSTEM: FATAL_BACKEND_ERROR — The 'image_gen' plugin is NOT installed. "
            "DO NOT call IMAGE_GEN or /img again! Inform the user directly that the Image Generation plugin is not installed.]"
        )
        new_done = update_image_turn_counters(
            missing_out, True, image_limit, images_already_done, sm
        )
        return {"id": call_id, "output": missing_out, "tag": "IMAGE_GEN"}, new_done

    return {
        "id": call_id,
        "output": (
            f"[SYSTEM ERROR: The plugin/module '{mod_upper}' is NOT installed or not active in Hecos. "
            f"Do NOT call '{mod_upper}' again. Inform the user that the '{mod_upper.lower()}' package is not installed.]"
        ),
        "tag": mod_upper,
    }, images_already_done

