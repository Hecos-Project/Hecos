"""

hecos/core/processing/tool_dispatcher.py

Orchestrates tool extraction and execution from AI responses.

Delegates limit checks to tool_limits.py and execution to tool_invoker.py.

"""



import json

import time

from typing import Any, Dict, List, Optional, Tuple



from hecos.core.logging import logger

from hecos.core.processing.parsers.reasoning_parser import ReasoningParser

from hecos.core.processing.parsers.json_fallback_parser import JsonFallbackParser

from hecos.core.processing.parsers.legacy_tag_parser import LegacyTagParser

from hecos.core.processing.tool_limits import (

    NUMBER_WORDS,

    get_requested_image_limit,

    is_image_tool_call,

    build_image_limit_exceeded_result,

    update_image_turn_counters,

)

from hecos.core.processing.tool_invoker import (

    execute_system_tool,

    execute_core_tool,

    execute_slash_command,

    execute_mcp_tool,

    execute_plugin_tool,

    build_missing_plugin_result,

)



# Backward-compatible aliases for internal helpers

_handle_system_tool = execute_system_tool

_handle_core_tool = execute_core_tool

_update_image_turn_counters = update_image_turn_counters



# Blacklist of tags to ignore

BLACKLIST = ["titolo", "anima", "regole", "database", "status", "tag", "block"]



# Mapping for generic tags to the correct module

TAG_MAPPING = {

    "terminal": "system",

    "cmd": "system",

    "instruction": "system",

    "open": "system",

    "notepad": "system",

    "chrome": "system",

    "visual studio": "system",

    "sillytavern": "system",

    "desktop": "system",

    "download": "system",

    "documents": "system",

    "core": "drive",

    "plugins": "drive",

    "memory": "drive",

    "personality": "drive",

    "logs": "drive",

    "config": "drive",

    "main": "drive",

    # Legacy fallbacks

    "terminale": "system",

    "istruzione": "system",

    "apri": "system",

    "documenti": "drive",

}





def _extract_native_tool_calls(raw_response: Any) -> Tuple[List[Tuple], bool]:

    """Extracts function/tool calls from structured LLM response objects."""

    tool_calls = getattr(raw_response, 'tool_calls', None)

    if not tool_calls and isinstance(raw_response, dict):

        tool_calls = raw_response.get('tool_calls')



    single_call = getattr(raw_response, 'function_call', None)

    if not tool_calls and single_call:

        tool_calls = [single_call] if not isinstance(single_call, list) else single_call



    is_tool_call_object = bool(tool_calls)

    tags_found: List[Tuple] = []



    if is_tool_call_object:

        logger.info("[PROCESSOR] Native Function Calling detected.")

        for call in tool_calls:

            f_obj = getattr(call, 'function', None) or getattr(call, 'function_call', None)

            if not f_obj and isinstance(call, dict):

                f_obj = call.get('function') or call.get('function_call')



            if not f_obj:

                continue



            f_name = getattr(f_obj, 'name', '') if not isinstance(f_obj, dict) else f_obj.get('name', '')

            f_args_raw = getattr(f_obj, 'arguments', '{}') if not isinstance(f_obj, dict) else f_obj.get('arguments', '{}')

            tag = None
            method = None

            try:
                args = f_args_raw if isinstance(f_args_raw, dict) else json.loads(f_args_raw)
            except Exception:
                args = {}

            if "__" in f_name:
                tag, method = f_name.split("__", 1)
            else:
                clean_name = f_name.strip().lower()
                # 1. Check if args wraps the method, e.g. {"generate_image": {"prompt": "..."}}
                if isinstance(args, dict):
                    for k, v in list(args.items()):
                        if isinstance(v, dict):
                            method = k
                            args = v
                            tag = clean_name
                            break
                        elif k.lower() in ("params", "arguments", "parameters", "input") and isinstance(v, dict):
                            args = v

                # 2. Known standard module/method mappings if not yet resolved
                if not method or not tag:
                    KNOWN_METHODS = {
                        "generate_image": ("image_gen", "generate_image"),
                        "probe_providers": ("image_gen", "probe_providers"),
                        "check_local_status": ("image_gen", "check_local_status"),
                        "web_search": ("netsearch", "web_search"),
                        "deep_search": ("netsearch", "deep_search"),
                        "search": ("netsearch", "web_search"),
                        "take_photo": ("webcam", "take_photo"),
                        "desktop_screenshot": ("webcam", "desktop_screenshot"),
                        "add_event": ("calendar", "add_event"),
                        "list_events": ("calendar", "list_events"),
                        "add_item": ("lists", "add_item"),
                        "get_items": ("lists", "get_items"),
                        "set_reminder": ("reminder", "set_reminder"),
                        "describe_module": ("system", "describe_module"),
                    }
                    if clean_name in KNOWN_METHODS:
                        tag, method = KNOWN_METHODS[clean_name]
                    elif clean_name in ("image_gen", "image_generator", "imagen"):
                        tag = "image_gen"
                        method = "generate_image"
                    elif clean_name in ("netsearch", "search_engine", "websearch"):
                        tag = "netsearch"
                        method = "web_search"
                    elif clean_name in ("webcam", "camera"):
                        tag = "webcam"
                        method = "take_photo"
                    else:
                        # Dynamic introspection fallback from get_tools_schema
                        try:
                            from hecos.core.system.module_docs import get_tools_schema
                            for t in get_tools_schema():
                                fn = t.get("function", {}).get("name", "")
                                if "__" in fn:
                                    t_tag, t_method = fn.split("__", 1)
                                    if clean_name == t_method.lower():
                                        tag, method = t_tag, t_method
                                        break
                                    elif clean_name == t_tag.lower():
                                        tag, method = t_tag, t_method
                                        break
                        except Exception:
                            pass

            if tag and method:
                call_id = getattr(call, 'id', None) if not isinstance(call, dict) else call.get('id')
                tags_found.append((tag.lower(), args, "function_call", method, call_id))
            else:
                logger.debug("PROCESSOR", f"Unknown function format: {f_name}")

    return tags_found, is_tool_call_object





def extract_and_execute_tools(

    raw_response: Any,

    current_config: dict,

    sm: Any = None,

) -> Tuple[bool, List[Dict[str, Any]], str, Optional[str]]:

    """

    Analyzes raw response, detects tools/tags, executes them, and returns results.

    Returns: (tools_called: bool, tool_results: list, base_text: str, think_block: str | None)

    """

    # 1. Ignore internal error messages from the Brain

    if isinstance(raw_response, str) and raw_response.startswith("⚠️"):

        logger.debug("PROCESSOR", "Ignoring internal HECOS error message for tag processing")

        return False, [], raw_response, None



    # 2. Extract structured tool calls if present

    tags_found, is_tool_call_object = _extract_native_tool_calls(raw_response)



    # 3. Extract base text safely

    if isinstance(raw_response, dict):

        base_text = raw_response.get('content', "") or ""

    elif not isinstance(raw_response, str):

        base_text = getattr(raw_response, 'content', "") or ""

    else:

        base_text = raw_response



    # 4. Extract <think> reasoning tags

    base_text, think_block = ReasoningParser.extract_reasoning(base_text)

    logger.debug("PROCESSOR", f"Processing text for tags: '{base_text[:200]}...'")



    # 4b. Guard: if tools are globally disabled by config, suppress tool execution completely

    if current_config.get("disable_tools", False):

        logger.debug("PROCESSOR", "Tools execution disabled by config. Returning text response.")

        return False, [], base_text, think_block



    # 5. Fallback JSON Parsing & Legacy Tag Parsing if no native calls were present

    if not is_tool_call_object:

        base_text, think_block = JsonFallbackParser.parse(base_text, tags_found, think_block)

        LegacyTagParser.parse(base_text, raw_response, tags_found)



    if not tags_found:

        return False, [], base_text, think_block



    # 6. Execute extracted tools

    tool_results: List[Dict[str, Any]] = []

    image_limit = getattr(sm, "requested_image_limit", 1) if sm else 1

    images_already_done = getattr(sm, "total_images_in_turn", 0) if sm else 0



    for tag_info in tags_found:

        if sm and getattr(sm, "webui_stop_requested", False):

            logger.warning("[PROCESSOR] Tool execution aborted by user via ESC.")

            break



        original_tag, action_or_args, call_type, method_name = tag_info[:4]

        call_id = tag_info[4] if len(tag_info) > 4 else f"call_{int(time.time())}"

        module_to_call = original_tag



        # Resolve generic tags (e.g. tag: terminal -> system)

        if original_tag == "tag" and not method_name and isinstance(action_or_args, str):

            clean_action = action_or_args.strip().lower()

            for keyword, module in TAG_MAPPING.items():

                if keyword in clean_action:

                    module_to_call = module

                    break

            else:

                continue



        if module_to_call in BLACKLIST:

            continue



        # Check image generation limits

        is_image_call = is_image_tool_call(original_tag, action_or_args, module_to_call, method_name)

        if is_image_call and images_already_done >= image_limit:

            exceeded_res = build_image_limit_exceeded_result(call_id, original_tag, image_limit, sm=sm)

            tool_results.append(exceeded_res)

            continue



        # Trace step initialization

        tool_step = None

        resolved_method_for_trace = method_name

        prev_results_count = len(tool_results)



        try:

            from hecos.core.agent.traces import AgentTracer

            from hecos.core.agent.trace_labeler import describe_tool_call

            t_desc = describe_tool_call(module_to_call, method_name, action_or_args)

            tool_step = AgentTracer.start_step(

                kind="command" if original_tag == "direct_command" else "tool",

                label=t_desc["full_label"],

                args_preview=t_desc["args_preview"],

                icon=t_desc["icon"],

                level="tool",

                module_name=t_desc["module_name"],

            )

        except Exception as _tr_err:

            logger.debug(f"[PROCESSOR] Trace start_step error: {_tr_err}")



        try:

            # Route A: Direct slash command

            if original_tag == "direct_command":

                res_dict, images_already_done = execute_slash_command(

                    action_or_args, call_id, current_config, is_image_call,

                    image_limit, images_already_done, sm=sm

                )

                tool_results.append(res_dict)

                continue



            # Route B: System builtins

            if module_to_call.upper() == "SYSTEM":

                res_sys = execute_system_tool(method_name, action_or_args, call_id, current_config)

                if res_sys is not None:

                    tool_results.append({"id": call_id, "output": str(res_sys), "tag": "SYSTEM"})

                continue



            # Route C: Core builtins

            if module_to_call.upper() == "CORE":

                res_core = execute_core_tool(method_name, action_or_args, call_id)

                if res_core is not None:

                    tool_results.append({"id": call_id, "output": str(res_core), "tag": "CORE"})

                continue



            # Ensure capability registry is populated

            from hecos.core.system import module_loader

            if not module_loader.get_active_tags():

                logger.info("[PROCESSOR] Plugin registry empty; performing lazy initialization...")

                module_loader.update_capability_registry(current_config, debug_log=False)



            # Route D: MCP Bridge tool

            mcp_res = execute_mcp_tool(module_to_call, method_name, action_or_args, call_id)

            if mcp_res is not None:

                tool_results.append(mcp_res)

                continue



            # Route E: Plugin module (native or legacy OOP)

            plugin_obj = module_loader.get_plugin_module(module_to_call.upper(), legacy=False)

            is_legacy_oop = False

            if not plugin_obj:

                plugin_obj = module_loader.get_plugin_module(module_to_call.upper(), legacy=True)

                if plugin_obj:

                    is_legacy_oop = True

                    logger.debug("PROCESSOR", f"Found legacy OOP plugin for {module_to_call}")

            else:

                logger.debug("PROCESSOR", f"Found native plugin for {module_to_call}")



            if plugin_obj:

                res_dict, resolved_method, images_already_done = execute_plugin_tool(

                    plugin_obj=plugin_obj,

                    is_legacy_oop=is_legacy_oop,

                    module_to_call=module_to_call,

                    method_name=method_name,

                    action_or_args=action_or_args,

                    call_id=call_id,

                    is_image_call=is_image_call,

                    image_limit=image_limit,

                    images_already_done=images_already_done,

                    sm=sm,

                )

                tool_results.append(res_dict)



                # Update trace step if method was resolved from arguments

                if resolved_method and resolved_method != method_name:

                    resolved_method_for_trace = resolved_method

                    if tool_step and not method_name:

                        try:

                            from hecos.core.agent.traces import AgentTracer

                            from hecos.core.agent.trace_labeler import describe_tool_call

                            r_desc = describe_tool_call(module_to_call, resolved_method, action_or_args)

                            tool_step["args_preview"] = r_desc["args_preview"]

                            tool_step["icon"] = r_desc["icon"]

                            AgentTracer.update_step(tool_step, label=r_desc["full_label"])

                        except Exception:

                            pass

            else:

                # Route F: Missing / uninstalled plugin

                missing_res, images_already_done = build_missing_plugin_result(

                    module_to_call, call_id, is_image_call, image_limit, images_already_done, sm=sm

                )

                tool_results.append(missing_res)



        finally:

            if tool_step is not None:

                try:

                    from hecos.core.agent.traces import AgentTracer

                    from hecos.core.agent.trace_labeler import summarize_tool_output

                    if len(tool_results) > prev_results_count:

                        last_out = tool_results[-1].get("output", "")

                        st, summary = summarize_tool_output(module_to_call, resolved_method_for_trace, last_out)

                        AgentTracer.finish_step(tool_step, status=st, result_preview=summary)

                    else:

                        AgentTracer.finish_step(tool_step, status="ok")

                except Exception as _fin_err:

                    logger.debug(f"[PROCESSOR] Trace finish_step error: {_fin_err}")



    return bool(tool_results), tool_results, base_text, think_block

