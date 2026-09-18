"""
MODULE: LiteLLM Client - Hecos (MANUAL LOGGING)
DESCRIPTION: Unified client for text generation via LiteLLM with re-routed logs.
"""

import litellm
import os
import json
import time
import logging
# Importiamo correttamente le funzioni dal modulo logger
from hecos.core.logging import logger as log_mod
from hecos.core.logging.logger import debug as zlog_debug, info as zlog_info, error as zlog_error

# Global variable to store last payload metadata for WebUI inspection
LAST_PAYLOAD_INFO = {
    "model": "None",
    "provider": "None",
    "system_chars": 0,
    "user_chars": 0,
    "tools_chars": 0,
    "total_chars": 0,
    "approx_tokens": 0,
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "messages_count": 0,
    "plugins_cost": {}
}

def get_active_model(cfg=None):
    """Returns the name of the last actively used model, falling back to config."""
    if LAST_PAYLOAD_INFO["model"] != "None":
        return LAST_PAYLOAD_INFO["model"]
    if cfg:
        btype = cfg.get("backend", {}).get("type", "ollama")
        if btype == "hybrid":
            cloud_m = cfg.get("backend", {}).get("cloud", {}).get("model", "")
            if cloud_m: return cloud_m
            btype = "ollama"
        return cfg.get("backend", {}).get(btype, {}).get("model", "?")
    return "?"

# Pre-configure LiteLLM (no print to chat)
litellm.telemetry = False

# CRITICAL: Disable remote cost map fetch to prevent startup timeouts (GitHub.com blocked/slow)
# LiteLLM: Falling back to local backup. (This avoids the 30s delay)
os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"

# CRITICAL: Purge any StreamHandlers LiteLLM added during import
_litellm_logger = logging.getLogger("LiteLLM")
for _h in _litellm_logger.handlers[:]:
    if isinstance(_h, logging.StreamHandler) and not isinstance(_h, logging.FileHandler):
        _litellm_logger.removeHandler(_h)
# Ensure LITELLM_LOG doesn't force verbose stdout output
os.environ["LITELLM_LOG"] = ""

def generate(system_prompt, user_message, config_or_subconfig, llm_config=None, tools=None, stream=False, images=None, extra_messages=None):
    """
    Genera una risposta usando LiteLLM.
    - images: optional list of dicts {data: bytes, mime_type: str, name: str}
    - extra_messages: optional list of dict objects to insert between system and user (for Agentic Loop).
    """
    
    # 1. Backend and Model Identification
    if 'backend' in config_or_subconfig:
        backend_info = config_or_subconfig.get('backend', {})
        backend_type = backend_info.get('type', 'ollama')
        specific_config = backend_info.get(backend_type, {})
        
        # Fallback for 'hybrid' mode if no explicit override is provided
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

    model_name = specific_config.get('model')
    
    if not model_name:
        return f"[SYSTEM] Error: Model not found."

    # 2. Configurazione Debug
    debug_enabled = llm_config.get('debug_llm', False) if llm_config else False
    
    # Prep di LiteLLM (niente print in chat)
    litellm.set_verbose = False
    
    # 3. Preparazione Messaggi
    provider = model_name.split('/')[0] if '/' in model_name else ""
    
    # ── Vision path: delegate to adapter if images are attached ──
    if images:
        try:
            from hecos.core.llm.vision.factory import get_vision_adapter
            adapter = get_vision_adapter(model_name, backend_type)
            if adapter:
                messages = adapter.build_messages(system_prompt, user_message, images)
                zlog_debug("LiteLLM", f"Vision adapter used: {adapter.__class__.__name__} ({len(images)} image(s))")
                
                # CRITICAL FIX: Even with images, we MUST include Agentic Loop history (tool results, etc.)
                if extra_messages:
                    messages.extend(extra_messages)
            else:
                # Adapter not available: fallback to text-only with a notice
                zlog_debug("LiteLLM", "No vision adapter for this model; falling back to text-only")
                images = None  # reset so text-only path runs below
        except Exception as ve:
            zlog_error(f"LiteLLM: Vision adapter error: {ve}")
            images = None

    # ── Text-only path ────────────────────────────────────────────
    if not images:
        messages = [{"role": "system", "content": system_prompt}]
        
        # OBIETTIVO AGENTE: Il messaggio utente deve precedere le chiamate tool
        messages.append({"role": "user", "content": user_message})
        
        # Inserimento messaggi extra (Agentic Loop: assistant tool-calls + tool results)
        if extra_messages:
            messages.extend(extra_messages)

    # Read cloud timeout from runtime-configurable global (settable via Key Manager UI)
    try:
        import hecos.core.keys.key_manager as _km_mod
        _cloud_timeout = getattr(_km_mod, "_KM_CLOUD_TIMEOUT", 30)
    except Exception:
        _cloud_timeout = 30

    params = {
        "model": model_name,
        "messages": messages,
        "temperature": specific_config.get('temperature', 0.7),
        "top_p": specific_config.get('top_p', 0.9),
        "num_retries": 0,  # We handle retries manually with key failover
        "stream": stream,
        "timeout": 300 if backend_type in ("ollama", "kobold", "llama_cpp") else _cloud_timeout,  # Cloud: configurable, Local: 5min
    }
    
    # Leggi preferenze per llama_cpp
    llama_native_tools = specific_config.get('native_tool_calling', True) if backend_type == "llama_cpp" else False
    llama_text_cmds = specific_config.get('text_commands_enabled', True) if backend_type == "llama_cpp" else False
    
    # Aggiungi i tools se presenti e se il backend lo supporta
    if tools and backend_type in ["cloud", "kobold"]:
        params["tools"] = tools
    
    # Per Ollama e llama_cpp
    if backend_type in ("ollama", "llama_cpp") and tools:
        if backend_type == "ollama" or (backend_type == "llama_cpp" and llama_native_tools):
            # Assicurati che ogni tool abbia "type": "function" per evitare l'Errore 400 su llama-server
            valid_tools = []
            for t in tools:
                if "type" not in t:
                    valid_tools.append({"type": "function", "function": t.get("function", t)})
                else:
                    valid_tools.append(t)
            params["tools"] = valid_tools

        # Inietta hint imperativo nel system prompt (sempre per ollama, condizionale per llama_cpp)
        if backend_type == "ollama" or (backend_type == "llama_cpp" and llama_text_cmds):
            if messages and messages[0].get("role") == "system":
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
                    # If not using native tools, do not inject JSON function schemas.
                    # The prompt_builder.py already injects slash command rules (e.g., /img).
                    tool_hint = "\n### CRITICAL: ACTIONS RULES ###\n"
                    tool_hint += "CRITICAL ANTI-REFUSAL: NEVER say 'I cannot generate images' or 'I am an AI'. You CAN generate images by emitting the /img command. DO IT!\n"
                    tool_hint += "You DO NOT have native JSON function calling. To perform actions like generating images, you MUST use the SLASH COMMANDS documented above (e.g. /img).\n"
                    tool_hint += "Do NOT copy placeholder brackets like [description]. Replace them with the actual description!\n"
                    messages[0]["content"] += tool_hint


    # 4. Configurazione Provider
    if backend_type == "ollama":
        if not model_name.startswith("ollama/"):
            params["model"] = f"ollama/{model_name}"
        params["api_base"] = specific_config.get('url', 'http://localhost:11434').rstrip('/')
        
        # CRITICAL: Parametri Ollama specifici per il caricamento GPU
        # Senza questi, LiteLLM usa solo i default di Ollama (nessuna GPU)
        ollama_options = {}
        
        num_gpu = specific_config.get('num_gpu')
        if num_gpu is not None:
            ollama_options["num_gpu"] = int(num_gpu)
        
        num_ctx = specific_config.get('num_ctx')
        if num_ctx is not None:
            ollama_options["num_ctx"] = int(num_ctx)
            
        num_predict = specific_config.get('num_predict')
        if num_predict is not None:
            ollama_options["num_predict"] = int(num_predict)
            
        repeat_penalty = specific_config.get('repeat_penalty')
        if repeat_penalty is not None:
            ollama_options["repeat_penalty"] = float(repeat_penalty)
            
        keep_alive = specific_config.get('keep_alive')
        if keep_alive is not None:
            ollama_options["keep_alive"] = keep_alive
            
        if ollama_options:
            params["extra_body"] = {"options": ollama_options}
        
        # DEBUG GPU - sempre attivo per Ollama
        zlog_info("LiteLLM", f"[OLLAMA GPU] Model: {params['model']}")
        zlog_info("LiteLLM", f"[OLLAMA GPU] Options being sent: {json.dumps(ollama_options)}")
        zlog_info("LiteLLM", f"[OLLAMA GPU] extra_body: {params.get('extra_body', 'NOT SET')}")

    elif backend_type == "kobold":
        if not model_name.startswith("openai/"):
            params["model"] = f"openai/{model_name}"
        params["api_base"] = specific_config.get('url', 'http://localhost:5001').rstrip('/') + "/v1"
        params["api_key"] = "sk-dummy"
        
    elif backend_type == "llama_cpp":
        # Auto-start Llama-cpp-python server
        try:
            from hecos.core.llm.backends.llama_cpp.server import server_manager
            n_gpu = specific_config.get('n_gpu_layers', -1)
            n_ctx = specific_config.get('n_ctx', 4096)
            threads = specific_config.get('threads', 4)
            zlog_info("LiteLLM", f"[LlamaCPP] Ensuring server is running for {model_name}...")
            # Automatically start/switch the server if not already running this model
            server_manager.start_server(model_name, n_gpu_layers=int(n_gpu), n_ctx=int(n_ctx), threads=int(threads))
            port = server_manager.port
        except Exception as e:
            zlog_error(f"LiteLLM: Error auto-starting LlamaCPP server: {e}")
            port = 8080

        if not model_name.startswith("openai/"):
            params["model"] = f"openai/{model_name}"
        # Point to the local openai-compatible server
        params["api_base"] = f"http://127.0.0.1:{port}/v1"
        params["api_key"] = "sk-dummy"

    elif backend_type == "cloud":
        # Assicurati che il modello includa il prefisso
        if '/' not in model_name and provider:
            params["model"] = f"{provider}/{model_name}"
        else:
            params["model"] = model_name
        
        # ── KeyManager: pool di chiavi con failover automatico ────────────
        try:
            from hecos.core.keys import get_key_manager
            _km = get_key_manager()
            api_key = _km.get_key(provider)
            if api_key:
                masked = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "***"
                zlog_info("LiteLLM", f"API key for '{provider}' from KeyManager ({masked})")
            else:
                zlog_error(f"LiteLLM: No available API key for provider '{provider}' in KeyManager.")
        except Exception as km_err:
            zlog_debug("LiteLLM", f"KeyManager not available ({km_err}), falling back to legacy lookup")
            api_key = None
            _km = None

        if api_key:
            params["api_key"] = api_key
            # LiteLLM in alcune versioni preferisce/richiede la env var per Gemini
            if provider == "gemini":
                os.environ["GEMINI_API_KEY"] = api_key
                # Apply the most permissive safety settings for Gemini (Imagen/Generative)
                # This helps reduce false-positive "spicy" blocks.
                params["safety_settings"] = [
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
                ]
        else:
            zlog_error(f"LiteLLM: No API key found for provider '{provider}'. Call may fail.")
        
        # Salviamo la chiave corrente usata per poter notificare il failover in caso di errore
        _current_api_key_for_provider = api_key

    # LOG MANUALE PRE-CHIAMATA E UPDATE PAYLOAD
    try:
        sys_chars = sum(len(str(m.get('content', ''))) for m in params.get("messages", []) if m.get('role') == 'system')
        usr_chars = sum(len(str(m.get('content', ''))) for m in params.get("messages", []) if m.get('role') != 'system')
        tls_chars = len(json.dumps(params.get("tools", []))) if params.get("tools") else 0
        tot_chars = sys_chars + usr_chars + tls_chars
        
        plugins_cost = {}
        for tool in params.get("tools", []):
            try:
                name = tool.get("function", {}).get("name", "")
                tag = name.split("__")[0] if "__" in name else "CORE_TOOLS"
                tool_size = len(json.dumps(tool))
                plugins_cost[tag] = plugins_cost.get(tag, 0) + tool_size
            except Exception:
                pass
        
        LAST_PAYLOAD_INFO.update({
            "model": model_name,
            "provider": backend_type,
            "system_chars": sys_chars,
            "user_chars": usr_chars,
            "tools_chars": tls_chars,
            "total_chars": tot_chars,
            "approx_tokens": tot_chars // 3,  # Approximate 1 token ~ 3-4 chars
            "prompt_tokens": 0,               # Reset prior counters
            "completion_tokens": 0,
            "messages_count": len(params.get("messages", [])),
            "plugins_cost": plugins_cost
        })
    except Exception as e:
        zlog_debug("LiteLLM", f"Payload analysis skipped: {e}")

    if debug_enabled:
        zlog_info("LiteLLM", f"Debug Activated for: {model_name}")
        try:
            # Avoid direct json.dumps on raw messages which might contain non-serializable objects
            # We log only non-sensitive and small metadata here
            safe_params = {k:v for k,v in params.items() if k not in ['api_key', 'tools', 'messages']}
            zlog_debug("LiteLLM", f"REQUEST_PARAMS (Metadata): {json.dumps(safe_params, indent=2)}")
            
            # --- Dedicated Payload Dump ---
            try:
                import datetime
                from hecos.core.constants import LOGS_DIR
                payload_log_path = os.path.join(LOGS_DIR, "payloads.log")
                dump_data = {
                    "timestamp": datetime.datetime.now().isoformat(),
                    "model": model_name,
                    "messages": params.get("messages", []),
                    "tools": params.get("tools", [])
                }
                with open(payload_log_path, "a", encoding="utf-8") as pf:
                    pf.write(json.dumps(dump_data, indent=2) + "\n\n" + "="*80 + "\n\n")
            except Exception as e:
                zlog_debug("LiteLLM", f"Could not dump payload to log: {e}")
                
        except Exception as sle:
            zlog_debug("LiteLLM", f"REQUEST_PARAMS: [Debug Log Error: {sle}]")


    # ── Retry loop with auto-failover ────────────────────────────────────
    from hecos.core.keys import get_key_manager as _get_km
    # Read max retries from runtime-configurable global (settable via Key Manager UI)
    try:
        import hecos.core.keys.key_manager as _km_settings
        _max_key_retries = getattr(_km_settings, "_KM_MAX_RETRIES", 5)
        # IMPORTANT: also use the actual pool size as the upper bound, so we never give up
        # before trying all available keys (e.g. if user has 9 keys but max_retries=5).
        try:
            _pool_size = len(_get_km()._pools.get(provider.lower(), [])) if provider else 0
            _max_key_retries = max(_max_key_retries, _pool_size)
        except Exception:
            pass
    except Exception:
        _max_key_retries = 5
    _tried_keys: list = []

    for _attempt in range(_max_key_retries):
        # On retry: get a fresh key from the pool, explicitly excluding already-tried ones
        if _attempt > 0 and backend_type == "cloud" and provider:
            try:
                _km2 = _get_km()
                _next_key = _km2.get_key(provider, exclude=_tried_keys)
                if not _next_key:
                    zlog_info("LiteLLM", f"[FAILOVER] No more available keys for '{provider}' after {_attempt} attempts.")
                    break
                params["api_key"] = _next_key
                if provider == "gemini":
                    os.environ["GEMINI_API_KEY"] = _next_key
                masked2 = f"{_next_key[:4]}...{_next_key[-4:]}" if len(_next_key) > 8 else "***"
                zlog_info("LiteLLM", f"[FAILOVER] Switching to key #{_attempt+1} for '{provider}' ({masked2})")
                _current_api_key_for_provider = _next_key
            except Exception:
                break

        _used_key = params.get("api_key", None)
        if _used_key:
            _tried_keys.append(_used_key)

        try:
            # ── OLLAMA DIRECT PATH: bypass LiteLLM to capture reasoning field ──
            # LiteLLM silently discards the `reasoning` field from Ollama's
            # /v1/chat/completions endpoint, losing all thinking content from
            # reasoning models (Qwen3.5, etc.). We call Ollama directly instead.
            if backend_type == "ollama" and not stream:
                import requests as _requests
                _ollama_base = params.get("api_base", "http://localhost:11434").rstrip("/")
                _ollama_url = f"{_ollama_base}/v1/chat/completions"
                
                # Build the request body — translate LiteLLM params to OpenAI format
                _ollama_body = {
                    "model": params["model"].replace("ollama/", "", 1),
                    "messages": params["messages"],
                    "temperature": params.get("temperature", 0.7),
                    "top_p": params.get("top_p", 0.9),
                    "stream": False,
                }
                # FIX #1: Forward tools to Ollama native tool calling (supported since Ollama 0.1.9)
                if params.get("tools"):
                    _ollama_body["tools"] = params["tools"]
                    zlog_debug("LiteLLM", f"[OLLAMA-DIRECT] Sending {len(params['tools'])} tools to Ollama")
                
                # Forward Ollama-specific options (num_gpu, num_ctx, etc.)
                _extra_body = params.get("extra_body")
                if _extra_body and "options" in _extra_body:
                    _ollama_body["options"] = _extra_body["options"]
                
                zlog_debug("LiteLLM", f"[OLLAMA-DIRECT] POST {_ollama_url} model={_ollama_body['model']}")
                
                _ollama_resp = _requests.post(
                    _ollama_url,
                    json=_ollama_body,
                    timeout=params.get("timeout", 300)
                )
                _ollama_resp.raise_for_status()
                _ollama_data = _ollama_resp.json()
                
                _ollama_msg = _ollama_data.get("choices", [{}])[0].get("message", {})
                _ollama_content = (_ollama_msg.get("content") or "").strip()
                _ollama_reasoning = _ollama_msg.get("reasoning") or _ollama_msg.get("reasoning_content") or ""
                
                # Update telemetry
                try:
                    _ollama_usage = _ollama_data.get("usage", {})
                    if _ollama_usage:
                        LAST_PAYLOAD_INFO["prompt_tokens"] = _ollama_usage.get("prompt_tokens", 0)
                        LAST_PAYLOAD_INFO["completion_tokens"] = _ollama_usage.get("completion_tokens", 0)
                        LAST_PAYLOAD_INFO["approx_tokens"] = _ollama_usage.get("total_tokens", LAST_PAYLOAD_INFO["approx_tokens"])
                except Exception:
                    pass
                
                # FIX #2: Handle tool_calls from Ollama response directly (no second LiteLLM call)
                _ollama_tool_calls = _ollama_msg.get("tool_calls")
                if _ollama_tool_calls:
                    zlog_debug("LiteLLM", f"[OLLAMA-DIRECT] Tool calls detected ({len(_ollama_tool_calls)}): {_ollama_tool_calls}")
                    # Build a synthetic message object that tool_dispatcher can parse
                    class _SyntheticMsg:
                        def __init__(self, tool_calls_raw, content):
                            self.role = "assistant"
                            self.content = content or ""
                            self.tool_calls = []
                            for tc in tool_calls_raw:
                                class _Call:
                                    pass
                                c = _Call()
                                c.id = tc.get("id", f"call_{int(time.time())}")
                                class _Fn:
                                    pass
                                fn = _Fn()
                                fn.name = tc.get("function", {}).get("name", "")
                                raw_args = tc.get("function", {}).get("arguments", {})
                                fn.arguments = json.dumps(raw_args) if isinstance(raw_args, dict) else (raw_args or "{}")
                                c.function = fn
                                self.tool_calls.append(c)
                        def model_dump(self):
                            return {
                                "role": self.role,
                                "content": self.content,
                                "tool_calls": [
                                    {"id": c.id, "type": "function",
                                     "function": {"name": c.function.name, "arguments": c.function.arguments}}
                                    for c in self.tool_calls
                                ]
                            }
                    return _SyntheticMsg(_ollama_tool_calls, _ollama_content)
                
                # ── FALLBACK A: Intercetta tool_calls JSON scritti nel testo ──
                if not _ollama_tool_calls and _ollama_content:
                    import re as _re_tc
                    _tc_match = _re_tc.search(r'\{[^{}]*"tool_calls"\s*:\s*\[.*?\]\s*\}', _ollama_content, _re_tc.DOTALL)
                    if _tc_match:
                        try:
                            _parsed_tc = json.loads(_tc_match.group())
                            if _parsed_tc.get("tool_calls"):
                                zlog_info("LiteLLM", "[OLLAMA-DIRECT] Recovered tool_calls from text output (fallback JSON parser)")
                                return _SyntheticMsg(_parsed_tc["tool_calls"], "")
                        except json.JSONDecodeError:
                            pass
                
                # ── FALLBACK B: Retry con reinforcement se il modello aveva tools ma non li ha usati ──
                if not _ollama_tool_calls and _ollama_content and params.get("tools") and not params.get("_tool_retry_done"):
                    # Il modello ha risposto con testo invece di chiamare un tool.
                    # Facciamo UN solo retry con un prompt di rinforzo.
                    params["_tool_retry_done"] = True  # Evita loop infiniti
                    zlog_info("LiteLLM", f"[OLLAMA-RETRY] Model responded with text instead of tool call. Attempting reinforcement retry...")
                    
                    _retry_messages = list(_ollama_body["messages"])  # Copia
                    _retry_messages.append({"role": "assistant", "content": _ollama_content})
                    _retry_messages.append({
                        "role": "user",
                        "content": (
                            "You did NOT call any tool. Your previous response was just text. "
                            "The user's request REQUIRES a tool call. "
                            "Please use the appropriate function call NOW. Do not respond with text."
                        )
                    })
                    
                    _retry_body = dict(_ollama_body)
                    _retry_body["messages"] = _retry_messages
                    
                    try:
                        _retry_resp = _requests.post(_ollama_url, json=_retry_body, timeout=params.get("timeout", 300))
                        _retry_resp.raise_for_status()
                        _retry_data = _retry_resp.json()
                        _retry_msg = _retry_data.get("choices", [{}])[0].get("message", {})
                        _retry_tool_calls = _retry_msg.get("tool_calls")
                        
                        if _retry_tool_calls:
                            zlog_info("LiteLLM", f"[OLLAMA-RETRY] SUCCESS! Tool call recovered on retry ({len(_retry_tool_calls)} calls)")
                            return _SyntheticMsg(_retry_tool_calls, _retry_msg.get("content", ""))
                        else:
                            # Anche il retry ha fallito — controlla JSON nel testo del retry
                            _retry_content = (_retry_msg.get("content") or "").strip()
                            if _retry_content:
                                _tc_match2 = _re_tc.search(r'\{[^{}]*"tool_calls"\s*:\s*\[.*?\]\s*\}', _retry_content, _re_tc.DOTALL)
                                if _tc_match2:
                                    try:
                                        _parsed_tc2 = json.loads(_tc_match2.group())
                                        if _parsed_tc2.get("tool_calls"):
                                            zlog_info("LiteLLM", "[OLLAMA-RETRY] Recovered tool_calls from retry text (fallback JSON parser)")
                                            return _SyntheticMsg(_parsed_tc2["tool_calls"], "")
                                    except json.JSONDecodeError:
                                        pass
                            zlog_info("LiteLLM", "[OLLAMA-RETRY] Retry also failed to produce tool call. Returning original response.")
                    except Exception as _retry_err:
                        zlog_error(f"LiteLLM: [OLLAMA-RETRY] Retry failed with error: {_retry_err}")
                
                zlog_debug("LiteLLM", f"[OLLAMA-DIRECT] content={len(_ollama_content)} chars | reasoning={len(_ollama_reasoning)} chars")
                
                if _ollama_reasoning:
                    zlog_info("LiteLLM", f"[REASONING] Captured {len(_ollama_reasoning)} chars of thinking from Ollama reasoning field")
                    # Re-inject as <think> tags so downstream ReasoningParser can extract them
                    import re
                    _ollama_content = re.sub(r'^(HECOS|Hecos|hecos)\s*:\s*', '', _ollama_content, flags=re.IGNORECASE)
                    return f"<think>\n{_ollama_reasoning}\n</think>\n\n{_ollama_content}"
                
                if not _ollama_content:
                    # Detect safety filter blocks
                    _finish = _ollama_data.get("choices", [{}])[0].get("finish_reason")
                    if _finish == "content_filter":
                        zlog_error("LiteLLM: Response BLOCKED by safety filter.")
                        return "!!!BLOCK_SAFETY!!!"
                    return ""
                
                import re
                _ollama_content = re.sub(r'^(HECOS|Hecos|hecos)\s*:\s*', '', _ollama_content, flags=re.IGNORECASE)
                return _ollama_content
            
            # ── STANDARD PATH: LiteLLM for cloud/kobold backends ──────────────
            response = litellm.completion(**params)

            if stream:
                return response  # Restituisce il generatore per lo stream in tempo reale

            # UPDATE TELEMETRY WITH REAL DATA
            try:
                usage = getattr(response, "usage", None)
                if usage:
                    LAST_PAYLOAD_INFO["prompt_tokens"] = getattr(usage, "prompt_tokens", 0)
                    LAST_PAYLOAD_INFO["completion_tokens"] = getattr(usage, "completion_tokens", 0)
                    LAST_PAYLOAD_INFO["approx_tokens"] = getattr(usage, "total_tokens", LAST_PAYLOAD_INFO["approx_tokens"])
            except Exception:
                pass

            # CONTROLLO SE HA USATO TOOLS
            choice = response.choices[0]
            msg = choice.message
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                if debug_enabled:
                    zlog_debug("LiteLLM", f"TOOL_CALLS: {msg.tool_calls}")
                return msg

            if debug_enabled:
                zlog_debug("LiteLLM", f"RESPONSE_OBJECT: {str(response)[:2000]}")

            # ── DIAGNOSTIC: log raw message fields to trace empty-content issues ──
            _raw_content = getattr(msg, 'content', None)
            _raw_reasoning = getattr(msg, 'reasoning_content', None)
            _raw_thinking = getattr(msg, 'thinking', None)
            _raw_reasoning2 = getattr(msg, 'reasoning', None)
            _provider_fields = {k: type(v).__name__ for k, v in vars(msg).items() if v} if hasattr(msg, '__dict__') else {}
            zlog_debug("LiteLLM", f"[DIAG] content={repr(_raw_content)[:200]} | reasoning_content={repr(_raw_reasoning)[:200]} | thinking={repr(_raw_thinking)[:200]} | reasoning={repr(_raw_reasoning2)[:200]}")
            zlog_debug("LiteLLM", f"[DIAG] msg non-null fields: {_provider_fields}")
            # Also check provider_specific_fields (litellm sometimes puts thinking data here)
            _prov_specific = getattr(msg, 'provider_specific_fields', None)
            if _prov_specific:
                zlog_debug("LiteLLM", f"[DIAG] provider_specific_fields: {repr(_prov_specific)[:500]}")

            if not msg.content:
                # For thinking models, reasoning content may be in a separate field
                _thinking = (
                    getattr(msg, 'reasoning_content', None) or
                    getattr(msg, 'thinking', None) or
                    getattr(msg, 'reasoning', None) or
                    ""
                )
                if _thinking:
                    zlog_debug("LiteLLM", f"Thinking model detected: content empty but reasoning found ({len(_thinking)} chars)")
                    return f"<think>{_thinking}</think>"
                
                # Detect if the response was blocked by a safety filter
                if getattr(choice, 'finish_reason', None) == 'content_filter' or getattr(response, 'prompt_feedback', {}).get('blockReason'):
                    zlog_error("LiteLLM: Response BLOCKED by safety filter.")
                    return "!!!BLOCK_SAFETY!!!"
                return ""
            content = msg.content.strip()
            import re
            content = re.sub(r'^(HECOS|Hecos|hecos)\s*:\s*', '', content, flags=re.IGNORECASE)
            return content

        except Exception as e:
            import traceback
            error_msg = str(e)
            error_type = type(e).__name__
            
            # Detailed logging so we can see EXACTLY why a call failed
            zlog_error(f"LiteLLM: [{error_type}] Error (attempt {_attempt + 1}/{_max_key_retries}) with model '{model_name}': {error_msg}")
            
            # Timeout: mark key as temporarily cooling and retry with next key
            if "Timeout" in error_type or "timeout" in error_msg.lower():
                zlog_error(f"LiteLLM: TIMEOUT on attempt {_attempt + 1}! Provider='{provider}', Model='{model_name}'.")
                # Mark the timed-out key as temporarily rate-limited (60s) so next request skips it
                _timed_out_key = params.get("api_key", None)
                if _timed_out_key and backend_type == "cloud" and provider:
                    try:
                        _km_err = _get_km()
                        _km_err.mark_exhausted(provider, _timed_out_key, "rate_limited", cooldown=60.0)
                        zlog_info("LiteLLM", f"[KeyManager] Timed-out key marked for 60s cooldown — trying next key.")
                    except Exception:
                        pass
                
                if _attempt == _max_key_retries - 1:
                    return f"⚠️ Timeout: The provider '{provider}' did not respond in {params.get('timeout', 30)}s after multiple attempts. Please try again later."
                continue

            # ── KeyManager: notify failure and attempt failover ──────────
            _failed_key = params.get("api_key", None)
            if _failed_key and backend_type == "cloud" and provider:
                try:
                    _km_err = _get_km()
                    if "401" in error_msg or "403" in error_msg or ("400" in error_msg and "API key not valid" in error_msg):
                        _km_err.mark_exhausted(provider, _failed_key, "invalid")
                        zlog_info("LiteLLM", f"[KeyManager] Key marked INVALID for '{provider}' — trying next.")
                    elif "429" in error_msg:
                        _km_err.mark_exhausted(provider, _failed_key, "rate_limited")
                        zlog_info("LiteLLM", f"[KeyManager] Key marked RATE_LIMITED for '{provider}' — trying next.")
                    else:
                        # Non-auth error: do not retry with a different key
                        pass
                except Exception:
                    pass

            # ── Only retry on auth/rate-limit errors ─────────────────────
            if "401" in error_msg or "403" in error_msg or "429" in error_msg:
                continue  # Retry with next key

            # ── Non-retryable errors: return immediately ──────────────────
            # Detect Ollama connection failures
            if backend_type == "ollama" and ("Connection" in error_type or "ConnectError" in error_type or "connection refused" in error_msg.lower() or "target machine actively refused it" in error_msg.lower()):
                _url = params.get("api_base", "http://localhost:11434")
                return f"⚠️ **Ollama Connection Failed**\nHecos cannot connect to the Ollama service at `{_url}`.\n\n**Please verify that:**\n1. Ollama is installed on your system.\n2. The Ollama application is currently open and running.\n3. You have pulled at least one model (e.g., run `ollama run qwen3.5` in your terminal)."

            if "400" in error_msg:
                return f"⚠️ Error 400: Invalid parameters for '{model_name}'. Details: {error_msg[:200]}"
            if "404" in error_msg:
                return f"⚠️ Error 404: The model '{model_name}' was not found or the endpoint is incorrect."
            if "503" in error_msg or "ServiceUnavailableError" in error_msg:
                return f"⚠️ AI Server Overloaded (Error 503). Provider {provider} is temporarily unavailable. Details: {error_msg[:100]}"
            return f"⚠️ Unexpected LLM Error [{error_type}]: {error_msg[:250]}"

    # All keys exhausted
    return f"⚠️ All API keys for '{provider}' are exhausted or invalid. Please add new keys in the Key Manager."