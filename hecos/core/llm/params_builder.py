"""
hecos/core/llm/params_builder.py
Constructs provider-specific parameters, handles vision message adapters,
and injects tool-calling guidelines into prompts.
"""

import os
import json
from typing import Any, Dict, List, Optional, Tuple

from hecos.core.logging.logger import debug as zlog_debug, info as zlog_info, error as zlog_error


def resolve_backend_and_model(config_or_subconfig: Dict[str, Any]) -> Tuple[str, str, Dict[str, Any]]:
    """Extracts the active backend type, model name, and specific configuration."""
    if 'backend' in config_or_subconfig:
        backend_info = config_or_subconfig.get('backend', {})
        backend_type = backend_info.get('type', 'ollama')
        specific_config = backend_info.get(backend_type, {})

        if backend_type == 'hybrid':
            cloud_conf = backend_info.get('cloud', {})
            ollama_conf = backend_info.get('ollama', {})
            if cloud_conf.get('model'):
                specific_config = cloud_conf
                backend_type = 'cloud'
            else:
                specific_config = ollama_conf
                backend_type = 'ollama'
    else:
        specific_config = config_or_subconfig
        backend_type = specific_config.get('backend_type', 'ollama')

    model_name = specific_config.get('model') or ""
    return backend_type, model_name, specific_config


def build_messages(
    system_prompt: str,
    user_message: str,
    images: Optional[List[Any]],
    extra_messages: Optional[List[Dict[str, Any]]],
    model_name: str,
    backend_type: str,
) -> List[Dict[str, Any]]:
    """Builds the message list, delegating to VisionAdapter if images are present."""
    if images:
        try:
            from hecos.core.llm.vision.factory import get_vision_adapter
            adapter = get_vision_adapter(model_name, backend_type)
            if adapter:
                messages = adapter.build_messages(system_prompt, user_message, images)
                zlog_debug("LiteLLM", f"Vision adapter used: {adapter.__class__.__name__} ({len(images)} image(s))")
                if extra_messages:
                    messages.extend(extra_messages)
                return messages
            zlog_debug("LiteLLM", "No vision adapter for this model; falling back to text-only")
        except Exception as ve:
            zlog_error(f"LiteLLM: Vision adapter error: {ve}")

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]
    if extra_messages:
        messages.extend(extra_messages)
    return messages


def inject_local_tool_hints(
    messages: List[Dict[str, Any]],
    params: Dict[str, Any],
    tools: Optional[List[Dict[str, Any]]],
) -> None:
    """Injects anti-refusal and tool-calling rules into system prompt for local models."""
    if not (messages and messages[0].get("role") == "system" and tools):
        return

    is_native = ("tools" in params)
    if is_native:
        tool_hint = "\n### CRITICAL: TOOL CALLING RULES ###\n"
        tool_hint += "You MUST use native function calls (JSON) to perform actions. NEVER describe or simulate performing an action in text.\n"
        tool_hint += "WRONG: 'Here is the photo I generated for you...' (NO tool was called!)\n"
        tool_hint += "RIGHT: Call the appropriate tool function with the correct parameters.\n\n"
        tool_hint += "Available tools:\n"
        for t in tools:
            fn = t.get("function", t)
            tool_hint += f"  - {fn.get('name', 'unknown')}: {fn.get('description', '')}\n"
        messages[0]["content"] += tool_hint
    else:
        tool_hint = "\n### CRITICAL: ACTIONS RULES ###\n"
        tool_hint += "CRITICAL ANTI-REFUSAL: NEVER say 'I cannot generate images' or 'I am an AI'. You CAN generate images by emitting the /img command. DO IT!\n"
        tool_hint += "You DO NOT have native JSON function calling. To perform actions like generating images, you MUST use the SLASH COMMANDS documented above (e.g. /img).\n"
        tool_hint += "Generate at most ONE image (/img) per turn unless the user explicitly requested multiple pictures (e.g. 'fanne 2').\n"
        tool_hint += "Do NOT copy placeholder brackets like [description]. Replace them with the actual description!\n"
        messages[0]["content"] += tool_hint


def build_llm_params(
    system_prompt: str,
    user_message: str,
    config_or_subconfig: Dict[str, Any],
    llm_config: Optional[Dict[str, Any]] = None,
    tools: Optional[List[Dict[str, Any]]] = None,
    stream: bool = False,
    images: Optional[List[Any]] = None,
    extra_messages: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[Optional[Dict[str, Any]], str, str, str, Dict[str, Any]]:
    """
    Constructs full request dictionary for LiteLLM or Ollama.
    Returns: (params, backend_type, model_name, provider, specific_config)
    """
    backend_type, model_name, specific_config = resolve_backend_and_model(config_or_subconfig)
    if not model_name:
        return None, backend_type, "", "", specific_config

    provider = model_name.split('/')[0] if '/' in model_name else ""
    messages = build_messages(system_prompt, user_message, images, extra_messages, model_name, backend_type)

    try:
        import hecos.core.keys.key_manager as _km_mod
        cloud_timeout = getattr(_km_mod, "_KM_CLOUD_TIMEOUT", 30)
    except Exception:
        cloud_timeout = 30

    params: Dict[str, Any] = {
        "model": model_name,
        "messages": messages,
        "temperature": specific_config.get('temperature', 0.7),
        "top_p": specific_config.get('top_p', 0.9),
        "num_retries": 0,
        "stream": stream,
        "timeout": 300 if backend_type in ("ollama", "kobold", "llama_cpp") else cloud_timeout,
    }

    llama_native_tools = specific_config.get('native_tool_calling', True) if backend_type == "llama_cpp" else False
    llama_text_cmds = specific_config.get('text_commands_enabled', True) if backend_type == "llama_cpp" else False

    if tools and backend_type in ["cloud", "kobold"]:
        params["tools"] = tools

    if backend_type in ("ollama", "llama_cpp") and tools:
        if backend_type == "ollama" or (backend_type == "llama_cpp" and llama_native_tools):
            valid_tools = []
            for t in tools:
                if "type" not in t:
                    valid_tools.append({"type": "function", "function": t.get("function", t)})
                else:
                    valid_tools.append(t)
            params["tools"] = valid_tools

        if backend_type == "ollama" or (backend_type == "llama_cpp" and llama_text_cmds):
            inject_local_tool_hints(messages, params, tools)

    # Provider specific routing
    if backend_type == "ollama":
        if not model_name.startswith("ollama/"):
            params["model"] = f"ollama/{model_name}"
        api_url = specific_config.get('url', 'http://127.0.0.1:11434').rstrip('/')
        params["api_base"] = api_url.replace("localhost", "127.0.0.1")

        ollama_options = {}
        for opt_key in ("num_gpu", "num_ctx", "num_predict", "repeat_penalty", "keep_alive"):
            val = specific_config.get(opt_key)
            if val is not None:
                ollama_options[opt_key] = float(val) if opt_key == "repeat_penalty" else (int(val) if opt_key != "keep_alive" else val)
        if ollama_options:
            params["extra_body"] = {"options": ollama_options}

        zlog_info("LiteLLM", f"[OLLAMA GPU] Model: {params['model']}")
        zlog_info("LiteLLM", f"[OLLAMA GPU] Options being sent: {json.dumps(ollama_options)}")

    elif backend_type == "kobold":
        if not model_name.startswith("openai/"):
            params["model"] = f"openai/{model_name}"
        params["api_base"] = specific_config.get('url', 'http://localhost:5001').rstrip('/') + "/v1"
        params["api_key"] = "sk-dummy"

    elif backend_type == "llama_cpp":
        try:
            from hecos.core.llm.backends.llama_cpp.server import server_manager
            n_gpu = specific_config.get('n_gpu_layers', -1)
            n_ctx = specific_config.get('n_ctx', 4096)
            threads = specific_config.get('threads', 4)
            zlog_info("LiteLLM", f"[LlamaCPP] Ensuring server is running for {model_name}...")
            server_manager.start_server(model_name, n_gpu_layers=int(n_gpu), n_ctx=int(n_ctx), threads=int(threads))
            port = server_manager.port
        except Exception as e:
            zlog_error(f"LiteLLM: Error auto-starting LlamaCPP server: {e}")
            port = 8080

        if not model_name.startswith("openai/"):
            params["model"] = f"openai/{model_name}"
        params["api_base"] = f"http://127.0.0.1:{port}/v1"
        params["api_key"] = "sk-dummy"

    elif backend_type == "cloud":
        if '/' not in model_name and provider:
            params["model"] = f"{provider}/{model_name}"
        else:
            params["model"] = model_name

        try:
            from hecos.core.keys import get_key_manager
            km = get_key_manager()
            api_key = km.get_key(provider)
            if api_key:
                masked = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "***"
                zlog_info("LiteLLM", f"API key for '{provider}' from KeyManager ({masked})")
            else:
                zlog_error(f"LiteLLM: No available API key for provider '{provider}' in KeyManager.")
        except Exception as km_err:
            zlog_debug("LiteLLM", f"KeyManager not available ({km_err}), falling back to legacy lookup")
            api_key = None

        if api_key:
            params["api_key"] = api_key
            if provider == "gemini":
                os.environ["GEMINI_API_KEY"] = api_key
                params["safety_settings"] = [
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                ]
        else:
            zlog_error(f"LiteLLM: No API key found for provider '{provider}'. Call may fail.")

    return params, backend_type, model_name, provider, specific_config

