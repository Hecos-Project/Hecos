"""
MODULE: LiteLLM Client - Zentra Core (MANUAL LOGGING)
DESCRIPTION: Unified client for text generation via LiteLLM with re-routed logs.
"""

import litellm
import os
import json
import logging
# Importiamo correttamente le funzioni dal modulo logger
from zentra.core.logging import logger as log_mod
from zentra.core.logging.logger import debug as zlog_debug, info as zlog_info, error as zlog_error

# Global variable to store last payload metadata for WebUI inspection
LAST_PAYLOAD_INFO = {
    "model": "None",
    "provider": "None",
    "system_chars": 0,
    "user_chars": 0,
    "tools_chars": 0,
    "total_chars": 0,
    "approx_tokens": 0,
    "messages_count": 0,
    "plugins_cost": {}
}

# Pre-configure LiteLLM (no print to chat)
litellm.telemetry = False

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
            from zentra.core.llm.vision.factory import get_vision_adapter
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

    params = {
        "model": model_name,
        "messages": messages,
        "temperature": specific_config.get('temperature', 0.7),
        "top_p": specific_config.get('top_p', 0.9),
        "num_retries": 1,
        "stream": stream
    }
    
    # Aggiungi i tools se presenti e se il backend lo supporta
    if tools and backend_type in ["cloud", "ollama", "kobold"]:
        params["tools"] = tools

    # 4. Configurazione Provider
    if backend_type == "ollama":
        if not model_name.startswith("ollama/"):
            params["model"] = f"ollama/{model_name}"
        params["api_base"] = "http://localhost:11434"
        
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

    elif backend_type == "cloud":
        # Assicurati che il modello includa il prefisso
        if '/' not in model_name and provider:
            params["model"] = f"{provider}/{model_name}"
        else:
            params["model"] = model_name
        
        # ── KeyManager: pool di chiavi con failover automatico ────────────
        try:
            from zentra.core.keys import get_key_manager
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
        except Exception as sle:
            zlog_debug("LiteLLM", f"REQUEST_PARAMS: [Debug Log Error: {sle}]")


    # ── Retry loop with auto-failover ────────────────────────────────────
    from zentra.core.keys import get_key_manager as _get_km
    _max_key_retries = 8  # max chiavi diverse da provare in sequenza
    _tried_keys: list = []

    for _attempt in range(_max_key_retries):
        # On retry: get a fresh key from the pool (skip already tried ones)
        if _attempt > 0 and backend_type == "cloud" and provider:
            try:
                _km2 = _get_km()
                _next_key = _km2.get_key(provider)
                # If we get the same key (or None), stop retrying
                if not _next_key or _next_key in _tried_keys:
                    break
                params["api_key"] = _next_key
                if provider == "gemini":
                    os.environ["GEMINI_API_KEY"] = _next_key
                masked2 = f"{_next_key[:4]}...{_next_key[-4:]}" if len(_next_key) > 8 else "***"
                zlog_info("LiteLLM", f"[FAILOVER] Switching to next key for '{provider}' ({masked2})")
                _current_api_key_for_provider = _next_key
            except Exception:
                break

        _used_key = params.get("api_key", None)
        if _used_key:
            _tried_keys.append(_used_key)

        try:
            response = litellm.completion(**params)

            if stream:
                return response  # Restituisce il generatore per il bridge WebUI

            # CONTROLLO SE HA USATO TOOLS
            msg = response.choices[0].message
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                if debug_enabled:
                    zlog_debug("LiteLLM", f"TOOL_CALLS: {msg.tool_calls}")
                return msg

            if debug_enabled:
                zlog_debug("LiteLLM", f"RESPONSE_OBJECT: {str(response)[:2000]}")

            if not msg.content:
                return ""
            content = msg.content.strip()
            import re
            content = re.sub(r'^(ZENTRA|Zentra|zentra)\s*:\s*', '', content, flags=re.IGNORECASE)
            return content

        except Exception as e:
            error_msg = str(e)
            zlog_error(f"LiteLLM: Error (attempt {_attempt + 1}): {error_msg}")

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
            if "400" in error_msg:
                return f"⚠️ Errore 400: Parametri non validi per '{model_name}'. Dettagli: {error_msg[:200]}"
            if "404" in error_msg:
                return f"⚠️ Errore 404: Il modello '{model_name}' non è stato trovato o l'endpoint è errato."
            if "503" in error_msg or "ServiceUnavailableError" in error_msg:
                return f"⚠️ Server AI Sovraccarico (Errore 503). Il provider {provider} è momentaneamente non disponibile. Dettagli: {error_msg[:100]}"
            return f"⚠️ Errore LLM imprevisto: {error_msg[:250]}"

    # All keys exhausted
    return f"⚠️ Tutte le chiavi API per '{provider}' sono esaurite o non valide. Aggiungi nuove chiavi nel Key Manager."