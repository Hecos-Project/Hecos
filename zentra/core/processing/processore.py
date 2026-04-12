"""
MODULE: Logical Processor - Zentra Core v2.5
DESCRIPTION: The 'execution engine'. Transforms AI thought into real actions 
via plugins and filters text for speech synthesis.
"""
import sys
import re
import os
import json
import time

import importlib.util
from zentra.core.llm import brain
from zentra.core.processing import filtri
from zentra.core.logging import logger
from zentra.core.i18n import translator

# Colors for terminal logs
YELLOW = '\033[93m'
CYAN = '\033[96m'
RED = '\033[91m'
RESET = '\033[0m'

# Global variable to hold hardware parameters
current_config = {}

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
    "core": "file_manager",

    "plugins": "file_manager",
    "memory": "file_manager",
    "personality": "file_manager",
    "logs": "file_manager",
    "config": "file_manager",
    "main": "file_manager",
    # Legacy fallbacks
    "terminale": "system",
    "istruzione": "system",
    "apri": "system",
    "documenti": "file_manager",
}

def configure(new_config):
    """Receives configuration from Main and stores it for Brain calls."""
    global current_config
    current_config = new_config
    logger.info("[PROCESSOR] Hardware configuration synchronized.")


def process_exchange(user_text, voice_status, sm=None):
    """Manages the entire chain: AI -> Plugin -> Cleaning -> Response.
    NOW REFACTORED TO USE THE AGENTIC LOOP."""
    logger.info(f"[PROCESSOR] Input received (length: {len(user_text)}). Delegating to Agentic Loop.")
    
    from zentra.core.agent.loop import AgentExecutor
    
    executor = AgentExecutor(config=current_config, state_manager=sm)
    video_response, clean_voice = executor.run_agentic_loop(user_text, voice_status=voice_status)
    return video_response, clean_voice


def extract_and_execute_tools(raw_response, config=None):
    """
    Analyzes raw response, detects tools/tags, executes them, and returns results.
    Returns: (tools_called: bool, tool_results: list, base_text: str)
    """
    global current_config
    if config:
        current_config = config

    # 1. Ignore error messages from the Brain
    if isinstance(raw_response, str) and raw_response.startswith("⚠️"):
        logger.debug("PROCESSOR", "Ignoring internal ZENTRA error message for tag processing")
        return False, [], raw_response

    # 1. Reasoning removal (<think> tags)
    if isinstance(raw_response, str):
        raw_response = re.sub(r'<think>.*?</think>', '', raw_response, flags=re.DOTALL | re.IGNORECASE).strip()
        raw_response = re.sub(r'<think>.*$', '', raw_response, flags=re.DOTALL | re.IGNORECASE).strip()
    
    tags_found = []
    
    # 2. Structured response (Native Function Calling)
    tool_calls = getattr(raw_response, 'tool_calls', None)
    if not tool_calls and isinstance(raw_response, dict):
        tool_calls = raw_response.get('tool_calls')
    
    single_call = getattr(raw_response, 'function_call', None)
    if not tool_calls and single_call:
        tool_calls = [raw_response]
        
    is_tool_call_object = bool(tool_calls)
    
    if is_tool_call_object:
        logger.info("[PROCESSOR] Native Function Calling detected.")
        for call in tool_calls:
            f_obj = getattr(call, 'function', None) or getattr(call, 'function_call', None)
            if not f_obj: continue
            
            f_name = getattr(f_obj, 'name', '')
            f_args_raw = getattr(f_obj, 'arguments', '{}')
            
            if "__" in f_name:
                tag, method = f_name.split("__", 1)
                try:
                    args = f_args_raw if isinstance(f_args_raw, dict) else json.loads(f_args_raw)
                except Exception as e:
                    args = {}
                tags_found.append((tag.lower(), args, "function_call", method, getattr(call, 'id', None)))
            else:
                logger.debug("PROCESSOR", f"Unknown function format: {f_name}")
        
        original_response_text = getattr(raw_response, 'content', "") or ""
        base_text = original_response_text
    else:
        if not isinstance(raw_response, str):
            raw_response = getattr(raw_response, 'content', "") or ""
            
        base_text = raw_response
        logger.debug("PROCESSOR", f"Processing text for tags: '{raw_response[:200]}...'")
        
        matches_standard = re.findall(r'\[(\w+):(.*?)\]', raw_response)
        for tag, action in matches_standard:
            tags_found.append((tag.lower(), action.strip(), "standard", None))
        
        matches_simple = re.findall(r'\[(\w+)\]', raw_response)
        for tag in matches_simple:
            if not any(t[0] == tag.lower() for t in tags_found):
                tags_found.append((tag.lower(), "", "simple", None))

    if not tags_found:
        return False, [], base_text
                
    # 3. Execution
    tool_results = []
    for tag_info in tags_found:
        # tag_info is (tag, args, type, method, optional_call_id)
        original_tag, action_or_args, call_type, method_name = tag_info[:4]
        call_id = tag_info[4] if len(tag_info) > 4 else f"call_{int(time.time())}"

        module_to_call = original_tag
        
        if original_tag == "tag" and not method_name and isinstance(action_or_args, str):
            clean_action = action_or_args.strip().lower()
            for keyword, module in TAG_MAPPING.items():
                if keyword in clean_action:
                    module_to_call = module
                    break
            else: continue
        
        if module_to_call in BLACKLIST: continue
            
        from zentra.core.system import plugin_loader
        
        # FAIL-SAFE: If the registry is empty (happens in standalone child processes), auto-init.
        if not plugin_loader.get_active_tags():
            logger.info("[PROCESSOR] Plugin registry empty; performing lazy initialization...")
            plugin_loader.update_capability_registry(current_config, debug_log=False)
            
        # --- NEW: Universal Tool Routing - Intercept MCP External Providers ---
        mcp_module = plugin_loader.get_plugin_module("MCP_BRIDGE", legacy=False)
        mcp_bridge_instance = getattr(mcp_module, "bridge_instance", None) if mcp_module else None
        
        if mcp_bridge_instance and hasattr(mcp_bridge_instance, "proxies"):
            # LLM tools are serialized as MCP_SERVERNAME__toolname
            # so module_to_call will be MCP_SERVERNAME (or lowercase mcp_servername)
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
                continue # Skip native plugin processing
        # ----------------------------------------------------------------------
        
        plugin_obj = plugin_loader.get_plugin_module(module_to_call.upper(), legacy=False)
        is_legacy_oop = False
        if not plugin_obj:
            plugin_obj = plugin_loader.get_plugin_module(module_to_call.upper(), legacy=True)
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
                # Handle both Native (method_name set) and Tag-based (extract from action_or_args)
                actual_method_name = method_name
                actual_args = action_or_args
                
                if not actual_method_name and isinstance(action_or_args, str) and ":" in action_or_args:
                    m_name, m_args = action_or_args.split(":", 1)
                    m_name = m_name.strip()
                    if hasattr(plugin_obj.tools, m_name):
                        actual_method_name = m_name
                        # If the method exists, we try to pass the rest as 'prompt' (common case)
                        # or as a single positional argument.
                        actual_args = {"prompt": m_args.strip()}
                
                if actual_method_name:
                    logger.info(f"[SYSTEM] {translator.t('executing_module', module=module_to_call.upper())}")
                    try:
                        method = getattr(plugin_obj.tools, actual_method_name)
                        # If it's a dict (from Native), unpack it. If it's the 'prompt' dict we just made, unpack it.
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
    
    return bool(tool_results), tool_results, base_text

# Tokens that must survive tag cleanup (intercepted by the browser JS)
_PRESERVED_TOKENS = ["[CAMERA_SNAPSHOT_REQUEST]"]

def clean_final_output(base_text, tool_results, raw_response_obj, voice_status=False):
    """Formats the final text for display and TTS after all loops are complete."""
    import re as _re
    # Temporarily protect special tokens from regex stripping
    _placeholders = {}
    for i, tok in enumerate(_PRESERVED_TOKENS):
        placeholder = f"__PRESERVED_{i}__"
        _placeholders[placeholder] = tok
        base_text = base_text.replace(tok, placeholder)
    
    # Protect [[IMG:...]] tags from the regex below
    _img_tags = _re.findall(r'\[\[IMG:[^\]]+\]\]', base_text)
    for j, img_tag in enumerate(_img_tags):
        marker = f"__IMG_{j}__"
        _placeholders[marker] = img_tag
        base_text = base_text.replace(img_tag, marker, 1)
    
    # Extract tags (for UI rendering if legacy tags were used instead of native functions)
    base_video = _re.sub(r'\[.*?:.*?\]', '', base_text).strip()
    base_video = _re.sub(r'\[.*?\]', '', base_video).strip()
    
    # Restore preserved tokens and IMG tags
    for placeholder, tok in _placeholders.items():
        base_video = base_video.replace(placeholder, tok)
    
    if not base_video:
        if tool_results:
            base_video = f"✅ {translator.t('command_executed_info', info='Tools Eseguiti')}"
        else:
            base_video = translator.t('model_no_response_error')
    
    video_response = filtri.clean_for_video(base_video)
    

    
    clean_voice_text = ""
    if voice_status:
        # We use base_video so Zentra speaks only her intention, not the raw JSON/logs.
        clean_voice_text = filtri.clean_for_voice(base_video)
        
    if tool_results:
        for r in tool_results:
            out = r.get('output', '')
            if not out:
                continue
            # If this is an image generation result, extract only the [[IMG:]] tag to show
            img_tags_in_out = _re.findall(r'\[\[IMG:[^\]]+\]\]', out)
            if img_tags_in_out:
                for img_tag in img_tags_in_out:
                    if img_tag not in video_response:
                        video_response += f"\n\n{img_tag}"
            else:
                # Append the raw output for non-image tools (e.g. system commands)
                video_response += f"\n\n{out}"
                
    # DEBUG: trace what REACHES the browser exactly at the exit point
    try:
        import datetime
        _pat = r'\[\[IMG:'
        _has_vr = bool(_re.search(_pat, video_response))
        _zentra_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
        _logs_dir = os.path.join(_zentra_dir, "logs")
        with open(os.path.join(_logs_dir, "image_gen_debug.txt"), "a", encoding="utf-8") as _f:
            _now = datetime.datetime.now().strftime("%H:%M:%S")
            _f.write(f"[{_now}] [ProcessorExitDebug] Final video_response (len={len(video_response)}, has_img={_has_vr}): {video_response[:200]}\n")
    except Exception:
        pass

    return video_response, clean_voice_text
