"""
hecos/core/processing/tool_dispatcher.py
Handles extraction and execution of tools/tags from AI responses.
Delegates to MCP, Core, System, and native/legacy Plugins.
"""
import time
import json
from hecos.core.logging import logger
from hecos.core.i18n import translator
from hecos.core.processing.parsers.reasoning_parser import ReasoningParser
from hecos.core.processing.parsers.json_fallback_parser import JsonFallbackParser
from hecos.core.processing.parsers.legacy_tag_parser import LegacyTagParser

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


NUMBER_WORDS = {
    'un': 1, 'uno': 1, 'una': 1, 'due': 2, 'tre': 3, 'quattro': 4, 'cinque': 5,
    'sei': 6, 'sette': 7, 'otto': 8, 'nove': 9, 'dieci': 10, 'undici': 11,
    'dodici': 12, 'tredici': 13, 'quattordici': 14, 'quindici': 15, 'sedici': 16,
    'diciassette': 17, 'diciotto': 18, 'diciannove': 19, 'venti': 20,
    'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6,
    'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10, 'eleven': 11, 'twelve': 12,
    'fifteen': 15, 'twenty': 20,
}

_WORD_OR_DIGIT_PATTERN = r'(\d+|' + '|'.join(NUMBER_WORDS.keys()) + r')'


def _parse_num_val(val: str | None) -> int | None:
    if not val:
        return None
    v = val.strip().lower()
    if v.isdigit():
        return int(v)
    return NUMBER_WORDS.get(v)


def get_requested_image_limit(user_text: str) -> int:
    """
    Parses user_text to check how many images/photos the user asked for.
    Supports numbers (digits or Italian/English words), parenthesized counts,
    and document requests with illustrations.
    Defaults to 1, with a safe ceiling of 20.
    """
    if not user_text or not isinstance(user_text, str):
        return 1
    t = user_text.lower()
    import re

    counts = []

    # 1. Explicit parentheses with number or word: e.g. (6), ( 6 ), (sei), (six)
    m_paren = re.search(r'\(\s*' + _WORD_OR_DIGIT_PATTERN + r'\s*(?:foto|fotografie|immagini|photos?|images?|pics?)?\s*\)', t)
    if m_paren:
        n = _parse_num_val(m_paren.group(1))
        if n and n >= 1:
            counts.append(n)

    # 2. Pattern: <verb> [ne/mi/ci] <number> e.g. 'devi farne 6', 'fanne 6', 'fammi 6', 'generane 6', 'generi 6', 'creane 6'
    m_verb = re.findall(
        r'\b(?:fai|fammi|fanne|farne|fare|faccene|facci|crea|creami|creane|creare|genera|generami|generane|generi|generare|manda|mandami|mandane|mandare|invia|inviami|inviane|mostra|mostrami|mostrane|produci|producimi|producine|disegna|disegnami|disegnane|scatta|scattami|scattane|voglio|vorrei|desidero|metti|inserisci|includi|allega|aggiungi|prepara|preparami|make|generate|create|produce|draw|take|want)\s+(?:almeno\s+|circa\s+)?' + _WORD_OR_DIGIT_PATTERN + r'\b',
        t
    )
    for match in m_verb:
        n = _parse_num_val(match)
        if n:
            counts.append(n)

    # 3. Pattern: <number> [di] <foto/immagini/images/photos>
    m_noun = re.findall(
        r'\b' + _WORD_OR_DIGIT_PATTERN + r'\s*(?:di\s+)?(?:foto|fotografie|immagini|immagine|photos?|pictures?|images?|pics?|illustrazioni|scatti)\b',
        t
    )
    for match in m_noun:
        n = _parse_num_val(match)
        if n:
            counts.append(n)

    # 4. Pattern: <foto/immagini> [:] [(] <number>
    m_after = re.findall(
        r'\b(?:foto|fotografie|immagini|immagine|photos?|pictures?|images?|pics?)\s*(?:sono|:|per\s+un\s+totale\s+di)?\s*' + _WORD_OR_DIGIT_PATTERN + r'\b',
        t
    )
    for match in m_after:
        n = _parse_num_val(match)
        if n:
            counts.append(n)

    if counts:
        # Take the maximum requested count (e.g. if user said 'fatto solo 2 foto devi farne 6' -> 6)
        return min(max(1, max(counts)), 20)

    # 5. If user asked for an illustrated document without explicit count, allow up to 6
    has_doc_intent = bool(re.search(r'\b(?:documento|doc|pdf|html|scheda)\b', t))
    has_img_intent = bool(re.search(r'\b(?:foto|immagini|illustrazioni|photos?|images?|illustrato|illustrata)\b', t))
    if has_doc_intent and has_img_intent:
        return 6

    return 1



def _handle_system_tool(method_name: str, args: dict, call_id: str, current_config: dict) -> str | None:
    """Dispatcher for built-in SYSTEM__ LLM tools."""
    if method_name == "describe_module":
        module_id = args.get("module_id", "") if isinstance(args, dict) else str(args).strip()
        if not module_id:
            return "Error: module_id parameter is required."
        try:
            from hecos.core.system.capability_inspector import build_card
            introspect = current_config.get("hpm", {}).get("auto_introspect", False) \
                if isinstance(current_config, dict) else False
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


def _handle_core_tool(method_name: str, args: dict, call_id: str) -> str | None:
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


def extract_and_execute_tools(raw_response, current_config: dict, sm=None):
    """
    Analyzes raw response, detects tools/tags, executes them, and returns results.
    Returns: (tools_called: bool, tool_results: list, base_text: str, think_block: str | None)
    """
    # 1. Ignore error messages from the Brain
    if isinstance(raw_response, str) and raw_response.startswith("⚠️"):
        logger.debug("PROCESSOR", "Ignoring internal HECOS error message for tag processing")
        return False, [], raw_response, None

    think_block = None
    tags_found = []
    
    # 1. Structured response (Native Function Calling)
    tool_calls = getattr(raw_response, 'tool_calls', None)
    if not tool_calls and isinstance(raw_response, dict):
        tool_calls = raw_response.get('tool_calls')
    
    single_call = getattr(raw_response, 'function_call', None)
    if not tool_calls and single_call:
        tool_calls = [single_call] if not isinstance(single_call, list) else single_call
        
    is_tool_call_object = bool(tool_calls)
    
    if is_tool_call_object:
        logger.info("[PROCESSOR] Native Function Calling detected.")
        for call in tool_calls:
            f_obj = getattr(call, 'function', None) or getattr(call, 'function_call', None)
            if not f_obj and isinstance(call, dict):
                f_obj = call.get('function') or call.get('function_call')
                
            if not f_obj: continue
            
            f_name = getattr(f_obj, 'name', '') if not isinstance(f_obj, dict) else f_obj.get('name', '')
            f_args_raw = getattr(f_obj, 'arguments', '{}') if not isinstance(f_obj, dict) else f_obj.get('arguments', '{}')
            
            if "__" in f_name:
                tag, method = f_name.split("__", 1)
                try:
                    args = f_args_raw if isinstance(f_args_raw, dict) else json.loads(f_args_raw)
                except Exception as e:
                    args = {}
                call_id = getattr(call, 'id', None) if not isinstance(call, dict) else call.get('id')
                tags_found.append((tag.lower(), args, "function_call", method, call_id))
            else:
                logger.debug("PROCESSOR", f"Unknown function format: {f_name}")
                
    # 2. Extract Base Text safely
    if isinstance(raw_response, dict):
        base_text = raw_response.get('content', "") or ""
    elif not isinstance(raw_response, str):
        base_text = getattr(raw_response, 'content', "") or ""
    else:
        base_text = raw_response
        
    # 3. Reasoning removal (<think> tags) via Modular Parser
    base_text, think_block = ReasoningParser.extract_reasoning(base_text)
    
    logger.debug("PROCESSOR", f"Processing text for tags: '{base_text[:200]}...'")
    
    # 4. Fallback JSON Parsing & Legacy Tag Parsing via Modular Parsers
    if not is_tool_call_object:
        base_text, think_block = JsonFallbackParser.parse(base_text, tags_found, think_block)
        LegacyTagParser.parse(base_text, raw_response, tags_found)

    if not tags_found:
        return False, [], base_text, think_block
                
    # 5. Execution
    tool_results = []
    image_limit = getattr(sm, "requested_image_limit", 1) if sm else 1
    images_already_done = getattr(sm, "total_images_in_turn", 0) if sm else 0

    for tag_info in tags_found:
        if sm and getattr(sm, "webui_stop_requested", False):
            logger.warning("[PROCESSOR] Tool execution aborted by user via ESC.")
            break
            
        original_tag, action_or_args, call_type, method_name = tag_info[:4]
        call_id = tag_info[4] if len(tag_info) > 4 else f"call_{int(time.time())}"
        
        if method_name:
            friendly_name = method_name.replace("_", " ").title()
            try:
                from hecos.core.agent.traces import AgentTracer
                AgentTracer.emit(None, f"Executing tool: {friendly_name}...", level="tool")
            except Exception:
                pass

        module_to_call = original_tag

        # Check if this tool is an image generation action
        is_image_call = False
        if original_tag == "direct_command" and isinstance(action_or_args, str):
            cmd_lower = action_or_args.strip().lower()
            if cmd_lower.startswith(("/img", "/image", "/photo", "/foto")):
                is_image_call = True
        elif module_to_call.upper() == "IMAGE_GEN" and (method_name == "generate_image" or not method_name):
            is_image_call = True

        if is_image_call and images_already_done >= image_limit:
            logger.warning(f"[PROCESSOR] Image generation limit reached ({image_limit}). Skipping duplicate/extra generation.")
            tool_results.append({
                "id": call_id,
                "output": f"[IMAGE_GEN: Limite di {image_limit} immagine/i per turno già raggiunto. L'immagine richiesta è già stata prodotta con successo. Concludi la risposta ora.]",
                "tag": "SLASH_COMMAND" if original_tag == "direct_command" else "IMAGE_GEN"
            })
            continue
        
        if original_tag == "direct_command":
            from hecos.core.commands.executor import get_executor
            executor = get_executor()
            try:
                # We do not have direct access to current_user_role/id here easily, so we fallback
                res = executor.execute(
                    raw_input=action_or_args,
                    config=current_config,
                    config_manager=None,
                    current_user_role="admin",
                    current_user_id="admin",
                    page_context="agent_internal"
                )
                if res.get("ok"):
                    output_val = res.get("output", "")
                    tool_results.append({"id": call_id, "output": output_val, "tag": "SLASH_COMMAND"})
                else:
                    output_val = f"Error: {res.get('error')}"
                    tool_results.append({"id": call_id, "output": output_val, "tag": "SLASH_COMMAND"})
                
                if is_image_call:
                    images_already_done += 1
                    if sm:
                        sm.total_images_in_turn = images_already_done
            except Exception as e:
                logger.error(f"[PROCESSOR] Error executing slash command: {e}")
                tool_results.append({"id": call_id, "output": f"Error: {e}", "tag": "SLASH_COMMAND"})
            continue
        
        if original_tag == "tag" and not method_name and isinstance(action_or_args, str):
            clean_action = action_or_args.strip().lower()
            for keyword, module in TAG_MAPPING.items():
                if keyword in clean_action:
                    module_to_call = module
                    break
            else: continue
        
        if module_to_call in BLACKLIST: continue
            
        from hecos.core.system import module_loader
        
        if not module_loader.get_active_tags():
            logger.info("[PROCESSOR] Plugin registry empty; performing lazy initialization...")
            module_loader.update_capability_registry(current_config, debug_log=False)
            
        mcp_module = module_loader.get_plugin_module("MCP_BRIDGE", legacy=False)
        mcp_bridge_instance = getattr(mcp_module, "bridge_instance", None) if mcp_module else None
        
        if mcp_bridge_instance and hasattr(mcp_bridge_instance, "proxies"):
            target_server = module_to_call[4:].lower() if module_to_call.upper().startswith("MCP_") else module_to_call.lower()
            
            resolved_server = None
            for p_name in mcp_bridge_instance.proxies.keys():
                if p_name.lower() == target_server:
                    resolved_server = p_name
                    break

            if resolved_server:
                logger.info(f"[SYSTEM] Routing external tool {method_name} to MCP Provider: {resolved_server}")
                try:
                    args_dict = action_or_args if isinstance(action_or_args, dict) else {}
                    result = mcp_bridge_instance.execute_mcp_tool(resolved_server, method_name, **args_dict)
                    if result:
                        logger.info(f"[OUTPUT MCP_{resolved_server.upper()}]:\n{result}")
                        tool_results.append({"id": call_id, "output": str(result), "tag": f"MCP_{resolved_server.upper()}"})
                except Exception as e:
                    logger.error(f"[PROCESSOR] MCP Tool error ({resolved_server}:{method_name}): {e}")
                    tool_results.append({"id": call_id, "output": f"Error: {e}", "tag": f"MCP_{resolved_server.upper()}"})
                continue 
        
        if module_to_call.upper() == "SYSTEM":
            result = _handle_system_tool(method_name, action_or_args, call_id, current_config)
            if result is not None:
                tool_results.append({"id": call_id, "output": str(result), "tag": "SYSTEM"})
            continue

        if module_to_call.upper() == "CORE":
            result = _handle_core_tool(method_name, action_or_args, call_id)
            if result is not None:
                tool_results.append({"id": call_id, "output": str(result), "tag": "CORE"})
            continue

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
            logger.debug("PROCESSOR", f"Analyzing plugin {module_to_call}: legacy_oop={is_legacy_oop}, has_tools={hasattr(plugin_obj, 'tools')}, has_execute={hasattr(plugin_obj, 'execute')}")
            
            if is_legacy_oop and (hasattr(plugin_obj, "process_tag") or hasattr(plugin_obj, "elabora_tag")):
                method_to_call = "process_tag" if hasattr(plugin_obj, "process_tag") else "elabora_tag"
                logger.info(f"[SYSTEM] {translator.t('executing_module', module=module_to_call.upper())}")
                try:
                    exec_method = getattr(plugin_obj, method_to_call)
                    result = exec_method(action_or_args)
                    if result:
                        logger.info(f"[OUTPUT {module_to_call.upper()}]:\n{result}")
                        tool_results.append({"id": call_id, "output": str(result), "tag": module_to_call.upper()})
                except Exception as e:
                    logger.error(f"[PROCESSOR] Legacy OOP error: {e}")
                    tool_results.append({"id": call_id, "output": f"Error: {e}", "tag": module_to_call.upper()})
            
            elif hasattr(plugin_obj, "tools"):
                actual_method_name = method_name
                actual_args = action_or_args
                
                if not actual_method_name and isinstance(action_or_args, str) and ":" in action_or_args:
                    m_name, m_args = action_or_args.split(":", 1)
                    m_name = m_name.strip()
                    if hasattr(plugin_obj.tools, m_name):
                        actual_method_name = m_name
                        actual_args = {"prompt": m_args.strip()}
                
                if actual_method_name:
                    logger.info(f"[SYSTEM] {translator.t('executing_module', module=module_to_call.upper())}")
                    try:
                        method = getattr(plugin_obj.tools, actual_method_name)
                        result = method(**actual_args) if isinstance(actual_args, dict) else method(actual_args)
                        if result:
                            logger.info(f"[OUTPUT {module_to_call.upper()}]:\n{result}")
                            tool_results.append({"id": call_id, "output": str(result), "tag": module_to_call.upper()})
                    except Exception as e:
                        logger.error(f"[PROCESSOR] Tool error ({actual_method_name}): {e}")
                        tool_results.append({"id": call_id, "output": f"Error: {e}", "tag": module_to_call.upper()})
                    
            elif hasattr(plugin_obj, "execute") and not method_name:
                logger.info(f"[SYSTEM] {translator.t('executing_module', module=module_to_call.upper())}")
                try:
                    result = plugin_obj.execute(action_or_args)
                    if result:
                        logger.info(f"[OUTPUT {module_to_call.upper()}]: {result}")
                        tool_results.append({"id": call_id, "output": str(result), "tag": module_to_call.upper()})
                except Exception as e:
                    logger.error(f"[PROCESSOR] Old Plugin error: {e}")
                    tool_results.append({"id": call_id, "output": f"Error: {e}", "tag": module_to_call.upper()})
            
            elif method_name:
                engine_target = getattr(plugin_obj, "get_plugin", lambda: plugin_obj)()
                if hasattr(engine_target, method_name):
                    logger.info(f"[SYSTEM] {translator.t('executing_module', module=module_to_call.upper())} → {method_name}")
                    try:
                        method = getattr(engine_target, method_name)
                        result = method(**action_or_args) if isinstance(action_or_args, dict) else method(action_or_args)
                        if result:
                            logger.info(f"[OUTPUT {module_to_call.upper()}]:\n{result}")
                            tool_results.append({"id": call_id, "output": str(result), "tag": module_to_call.upper()})
                            if is_image_call and ("[[IMG:" in str(result) or "gen_" in str(result)):
                                images_already_done += 1
                                if sm:
                                    sm.total_images_in_turn = images_already_done
                    except Exception as e:
                        logger.error(f"[PROCESSOR] Direct method error ({module_to_call}.{method_name}): {e}")
                        tool_results.append({"id": call_id, "output": f"Error: {e}", "tag": module_to_call.upper()})
    
    return bool(tool_results), tool_results, base_text, think_block
