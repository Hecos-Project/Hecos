"""



hecos/core/llm/params_builder.py



Constructs provider-specific parameters, handles vision message adapters,



and injects tool-calling guidelines into prompts.



"""







import os



import json



from typing import Any, Dict, List, Optional, Tuple







from hecos.core.logging.logger import debug as zlog_debug, info as zlog_info, error as zlog_error

import requests



# Cache for model family detection (avoid repeated Ollama API calls)

_model_family_cache: dict = {}



def _is_gemma4_model(model_name: str, api_base: str = "http://localhost:11434") -> bool:

    """

    Checks if the given Ollama model uses the gemma4 renderer/parser.

    Gemma 4 models use an internal channel-based reasoning system that is

    incompatible with the OpenAI-style tools API. When tools are passed to

    Ollama with a gemma4 renderer, the system message is overwritten and

    internal tokens leak into the output.

    Returns True if the model is gemma4 family and tools should NOT be passed natively.

    """

    cache_key = f"{api_base}::{model_name}"

    if cache_key in _model_family_cache:

        return _model_family_cache[cache_key]

    try:

        clean_name = model_name.replace("ollama/", "", 1)

        # Try the configured URL first, then fallback alternatives
        # (Ollama may listen on localhost but not 127.0.0.1 or vice versa)
        urls_to_try = [api_base]
        if "127.0.0.1" in api_base:
            urls_to_try.append(api_base.replace("127.0.0.1", "localhost"))
        elif "localhost" in api_base:
            urls_to_try.append(api_base.replace("localhost", "127.0.0.1"))

        last_exc = None
        for url in urls_to_try:
            try:
                r = requests.post(
                    f"{url}/api/show",
                    json={"name": clean_name},
                    timeout=3.0
                )
                if r.status_code == 200:
                    data = r.json()

                    # Check RENDERER field in modelfile
                    modelfile = data.get("modelfile", "")

                    if "RENDERER gemma4" in modelfile or "PARSER gemma4" in modelfile:
                        _model_family_cache[cache_key] = True
                        zlog_info("LiteLLM", f"[GEMMA4 DETECT] '{clean_name}' uses gemma4 renderer - disabling native tool API")
                        return True

                    # Also check model family in details
                    families = data.get("details", {}).get("families", [])

                    if "gemma4" in families:
                        _model_family_cache[cache_key] = True
                        zlog_info("LiteLLM", f"[GEMMA4 DETECT] '{clean_name}' is gemma4 family - disabling native tool API")
                        return True

                    _model_family_cache[cache_key] = False
                    return False
            except Exception as exc:
                last_exc = exc
                continue

        # All URLs failed
        raise last_exc or Exception("All Ollama URLs unreachable")

    except Exception as e:

        zlog_debug("LiteLLM", f"[GEMMA4 DETECT] Could not check model family for '{model_name}': {e}")

        _model_family_cache[cache_key] = False

        return False















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



    history_turns: Optional[List[Dict[str, Any]]] = None,



) -> List[Dict[str, Any]]:



    """Builds the message list, delegating to VisionAdapter if images are present."""



    if images:



        try:



            from hecos.core.llm.vision.factory import get_vision_adapter



            adapter = get_vision_adapter(model_name, backend_type)



            if adapter:



                messages = adapter.build_messages(system_prompt, user_message, images)



                zlog_debug("LiteLLM", f"Vision adapter used: {adapter.__class__.__name__} ({len(images)} image(s))")



                if history_turns and len(messages) >= 2:



                    history_msgs = [{"role": t.get("role", "user"), "content": t.get("content", "")} for t in history_turns]



                    messages = [messages[0]] + history_msgs + messages[1:]



                if extra_messages:



                    messages.extend(extra_messages)



                return messages



            zlog_debug("LiteLLM", "No vision adapter for this model; falling back to text-only")



        except Exception as ve:



            zlog_error(f"LiteLLM: Vision adapter error: {ve}")







    messages = [{"role": "system", "content": system_prompt}]



    if history_turns:



        for t in history_turns:



            messages.append({"role": t.get("role", "user"), "content": t.get("content", "")})



    messages.append({"role": "user", "content": user_message})



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



    is_native = bool(tools and "tools" in params)

    if is_native:

        tool_hint = (

            "\n### ACTIONS & TOOL EXECUTION RULES ###\n"

            "To perform actions, use native JSON function calls OR direct slash commands (e.g. `/img <description>` to generate images, `/search <query>` to search the web).\n"

            "If the user explicitly asks for an image or action, execute the appropriate tool. Do NOT use image or action tools unless the user explicitly requests them.\n"

            "Always stay in character with your active personality and identity.\n"

        )

        messages[0]["content"] += tool_hint

    else:

        tool_hint = (

            "\n### DIRECT ACTIONS RULES (SLASH COMMANDS) ###\n"

            "You have action modules available via slash commands. Use them ONLY when the user explicitly requests an action.\n"

            "- IF the user explicitly asks you to generate or draw an image/photo: output `/img <english_prompt>` on its own line.\n"

            "- IF the user explicitly asks you to search the web: output `/search <query>` on its own line.\n"

            "Do NOT use slash commands unless the user has explicitly requested that specific action in their message.\n"

            "Always stay in character with your active personality and identity.\n"

        )

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



    history_turns = specific_config.get("history_turns")



    messages = build_messages(



        system_prompt=system_prompt,



        user_message=user_message,



        images=images,



        extra_messages=extra_messages,



        model_name=model_name,



        backend_type=backend_type,



        history_turns=history_turns,



    )







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







    if backend_type in ("ollama", "llama_cpp"):



        if tools:



            if backend_type == "ollama" or (backend_type == "llama_cpp" and llama_native_tools):



                # Check if the model is gemma4: gemma4 uses an internal channel-based

                # reasoning system incompatible with the OpenAI tools API.

                # For gemma4, skip native tool injection and use text hints only.

                _api_url = specific_config.get("url", "http://127.0.0.1:11434")

                _skip_native = _is_gemma4_model(model_name, _api_url)



                if not _skip_native:

                    valid_tools = []



                    for t in tools:



                        if "type" not in t:



                            valid_tools.append({"type": "function", "function": t.get("function", t)})



                        else:



                            valid_tools.append(t)



                    params["tools"] = valid_tools



                else:

                    zlog_info("LiteLLM", "[GEMMA4] Skipping native tools API - using text-only tool hints for gemma4 model")







        if backend_type == "ollama" or (backend_type == "llama_cpp" and llama_text_cmds):



            inject_local_tool_hints(messages, params, tools)







    # Provider specific routing



    if backend_type == "ollama":



        if not model_name.startswith("ollama/"):



            params["model"] = f"ollama/{model_name}"



        api_url = specific_config.get('url', 'http://127.0.0.1:11434').rstrip('/')



        params["api_base"] = api_url.replace("localhost", "127.0.0.1")







        # --- VRAM Adaptive Engine: override num_ctx based on available VRAM ---

        try:

            from hecos.core.llm.adaptive import get_optimal_num_ctx

            _adaptive_ctx = get_optimal_num_ctx(specific_config)

            if _adaptive_ctx is not None:

                specific_config = dict(specific_config)  # shallow copy, don't mutate source

                specific_config["num_ctx"] = _adaptive_ctx

        except Exception as _vae:

            pass  # Adaptive engine is optional — never break the LLM call



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







