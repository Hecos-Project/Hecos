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

        # Do NOT cache connection/startup errors permanently — Ollama may still be booting.
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











def _build_dynamic_text_mode_catalog(
    tools: List[Dict[str, Any]],
    config: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Build a concise, 100% dynamic text-mode tool catalog directly from active tool schemas,
    dormant lazy HPM schemas (when tool_selection_mode == 'all'), and registry slash commands.
    Zero hardcoded module directives.
    """
    import json as _json
    import os as _os

    cfg = config if isinstance(config, dict) else {}
    p_ctrl = cfg.get("payload_control") or {}
    if cfg.get("disable_tools", False) or not p_ctrl.get("send_tools", True):
        return ""

    sel_mode = str(p_ctrl.get("tool_selection_mode") or "all").strip().lower()
    cfg_plugins = cfg.get("plugins") or {}
    is_plan_only = bool(cfg.get("_turn_plan_only") or cfg.get("_turn_revise_plan_id")) and not bool(
        cfg.get("_turn_execute_plan") or cfg.get("_turn_fast_code")
    )
    _plan_only_blocked = {
        "EXECUTOR__write_file", "EXECUTOR__patch_file", "EXECUTOR__run_aider_task",
        "EXECUTOR__delete_file", "EXECUTOR__move_path", "EXECUTOR__create_dir",
        "EXECUTOR__start_app", "EXECUTOR__stop_app", "EXECUTOR__git_restore",
        "EXECUTOR__execute_shell_command", "EXECUTOR__run_python_code",
        "IMAGE_GEN__generate_image", "ACTION_PLANS__update_step", "ACTION_PLANS__complete_plan",
    }
    _internal_skip_tags = {"MEMORY", "MODELS", "PERSONALITY", "WEB_UI", "HELP"}

    combined_schemas: List[Dict[str, Any]] = list(tools or [])
    seen_fnames = set()
    for _t in combined_schemas:
        if isinstance(_t, dict):
            _fn = _t.get("function") if isinstance(_t.get("function"), dict) else _t
            _n = str(_fn.get("name") or "").strip()
            if _n:
                seen_fnames.add(_n)

    # In 'all' mode, also include dormant lazy HPM schemas (e.g. IMAGE_GEN, CALENDAR, REMINDER, WEBCAM)
    # since text-mode sends 0 JSON tool schemas to the backend and needs compact syntax visibility.
    if sel_mode != "custom":
        try:
            from hecos.core.system.module_state import _lazy_tool_schemas, _lazy_llm_callable
            for tag, lazy_list in list(_lazy_tool_schemas.items()):
                tag_up = str(tag or "").upper()
                if not tag_up or tag_up in _internal_skip_tags:
                    continue
                if not cfg_plugins.get(tag_up, {}).get("enabled", True):
                    continue
                if not cfg_plugins.get(tag_up, {}).get("llm_callable", True):
                    continue
                if not _lazy_llm_callable.get(tag_up, True):
                    continue
                for _lt in (lazy_list or []):
                    if not isinstance(_lt, dict):
                        continue
                    _fn = _lt.get("function") if isinstance(_lt.get("function"), dict) else _lt
                    _fname = str(_fn.get("name") or "").strip()
                    if not _fname or _fname in seen_fnames:
                        continue
                    if is_plan_only and _fname in _plan_only_blocked:
                        continue
                    seen_fnames.add(_fname)
                    combined_schemas.append(_lt)
        except Exception:
            pass

    # Load registered slash commands per tag from registry.json (for compact '| Slash: ...' hints)
    slash_by_tag: Dict[str, List[str]] = {}
    try:
        from hecos.core.system.module_state import REGISTRY_PATH
        if _os.path.exists(REGISTRY_PATH):
            with open(REGISTRY_PATH, "r", encoding="utf-8") as _rf:
                _reg = _json.load(_rf) or {}
            for _rtag, _rinfo in _reg.items():
                if not isinstance(_rinfo, dict):
                    continue
                _usages: List[str] = []
                for _sc in (_rinfo.get("slash_commands") or []):
                    if isinstance(_sc, dict):
                        _u = str(_sc.get("usage") or "").strip()
                        if not _u and _sc.get("aliases"):
                            _u = str(_sc["aliases"][0]).strip()
                        if _u:
                            _usages.append(_u)
                    elif isinstance(_sc, str) and _sc.strip():
                        _usages.append(_sc.strip())
                if _usages:
                    slash_by_tag[str(_rtag).upper()] = list(dict.fromkeys(_usages))
    except Exception:
        pass

    grouped: Dict[str, List[str]] = {}
    for _t in combined_schemas:
        if not isinstance(_t, dict):
            continue
        _fn = _t.get("function") if isinstance(_t.get("function"), dict) else _t
        _fname = str(_fn.get("name") or "").strip()
        if not _fname:
            continue
        _tag = _fname.split("__", 1)[0].upper() if "__" in _fname else "TOOLS"
        if _tag in _internal_skip_tags:
            continue
        _params_obj = _fn.get("parameters") or {}
        _req = [str(p) for p in (_params_obj.get("required") or []) if p]
        if not _req:
            _props = list((_params_obj.get("properties") or {}).keys())
            _sig_args = ", ".join(f"{p}=?" for p in _props[:2])
        else:
            _sig_args = ", ".join(_req[:4])
        grouped.setdefault(_tag, []).append(f"{_fname}({_sig_args})")

    if not grouped:
        return ""

    lines: List[str] = []
    for _tag in sorted(grouped.keys()):
        _sigs = grouped[_tag]
        _shown = ", ".join(_sigs[:10])
        if len(_sigs) > 10:
            _shown += f" (+{len(_sigs) - 10} more)"
        _slash_list = slash_by_tag.get(_tag) or []
        _slash_part = f" | Slash: {', '.join(_slash_list[:3])}" if _slash_list else ""
        lines.append(f"- {_tag}: {_shown}{_slash_part}")

    return (
        "\n### DIRECT ACTIONS (TEXT-MODE TOOL CALLS) ###\n"
        "Native JSON tool calling is inactive for this model. To execute any active tool below, "
        "emit `MODULE__method(arg='value')`, `[MODULE: method(arg='value')]`, or its slash command on its own line. "
        "When multiple actions are requested, emit one call per line. "
        "Always wait for real tool output before reporting results; never simulate tool results in plain text.\n"
        + "\n".join(lines)
        + "\n"
    )


def inject_local_tool_hints(
    messages: List[Dict[str, Any]],
    params: Dict[str, Any],
    tools: Optional[List[Dict[str, Any]]],
    config: Optional[Dict[str, Any]] = None,
) -> None:
    """Injects native or dynamically generated text-mode tool syntax into the system prompt for local models."""
    if not (messages and messages[0].get("role") == "system" and tools):
        return

    is_native = bool(tools and "tools" in params)
    if is_native:
        tool_hint = (
            "\n### ACTIONS & TOOL EXECUTION RULES ###\n"
            "Action modules can be invoked via tool calls when requested by the user.\n"
        )
        messages[0]["content"] += tool_hint
    else:
        dynamic_catalog = _build_dynamic_text_mode_catalog(tools, config=config)
        if dynamic_catalog:
            messages[0]["content"] += dynamic_catalog



def _resolve_local_llm_timeout(specific_config: Dict[str, Any]) -> int:
    """Resolve HTTP timeout (seconds) for local backends from backend config or Key Manager UI override."""
    default_local = 900
    raw_cfg = specific_config.get("request_timeout_sec") or specific_config.get("timeout")
    try:
        cfg_val = int(raw_cfg) if raw_cfg is not None else default_local
    except (TypeError, ValueError):
        cfg_val = default_local
    try:
        import hecos.core.keys.key_manager as _km_mod
        km_webui = int(getattr(_km_mod, "_KM_WEBUI_INFERENCE_TIMEOUT", 0) or 0)
    except Exception:
        km_webui = 0
    return max(60, min(3600, max(cfg_val, km_webui)))


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



        "timeout": _resolve_local_llm_timeout(specific_config) if backend_type in ("ollama", "kobold", "llama_cpp") else cloud_timeout,



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

            inject_local_tool_hints(messages, params, tools, config=config_or_subconfig)







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



        # Inject think=false if enable_thinking is explicitly disabled
        # payload_control is at root of config_or_subconfig (set by brain.py), NOT inside specific_config (ollama sub-dict)
        # NOTE: for Gemma4 and most Ollama models, "think" must be a ROOT-level key in the request body, NOT inside options{}
        _pctrl = config_or_subconfig.get("payload_control") or specific_config.get("payload_control") or {}
        _thinking_enabled = _pctrl.get("enable_thinking")  # None = not set, False = disabled
        if _thinking_enabled is None:
            _thinking_enabled = specific_config.get("enable_thinking")
        _think_root = None  # will be injected at root level of ollama body, not inside options
        if _thinking_enabled is False:
            _think_root = False
            zlog_info("LiteLLM", "[OLLAMA GPU] Thinking DISABLED (think=false at root level) for this session.")

        for opt_key in ("num_gpu", "num_ctx", "num_predict", "repeat_penalty", "keep_alive"):



            val = specific_config.get(opt_key)



            if val is not None:



                ollama_options[opt_key] = float(val) if opt_key == "repeat_penalty" else (int(val) if opt_key != "keep_alive" else val)



        if ollama_options or _think_root is not None:



            params["extra_body"] = {"options": ollama_options}
            if _think_root is not None:
                params["extra_body"]["think"] = _think_root







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







