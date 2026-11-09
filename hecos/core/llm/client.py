"""
MODULE: LiteLLM Client - Hecos (MANUAL LOGGING)
DESCRIPTION: Unified client for text generation via LiteLLM with re-routed logs.
Delegates telemetry tracking to payload_tracker.py, parameter setup to params_builder.py,
and direct Ollama calls to backends/ollama_direct.py.
"""

import os
import json
import logging
import re
from typing import Any, Dict, List, Optional

# Force WARNING before importing litellm so its module-init AiohttpTransport logs
# never dump raw DEBUG lines onto stderr during import. File-based DEBUG logging
# is attached explicitly below via Hecos's logger handlers.
os.environ["LITELLM_LOG"] = "WARNING"
import litellm

from hecos.core.logging.logger import (
    debug as zlog_debug,
    info as zlog_info,
    error as zlog_error,
    sync_litellm_loggers,
)
from hecos.core.llm.payload_tracker import (
    LAST_PAYLOAD_INFO,
    get_active_model,
    analyze_and_record_payload,
    update_usage_telemetry,
    dump_debug_payload,
)
from hecos.core.llm.params_builder import build_llm_params
from hecos.core.llm.backends.ollama_direct import execute_ollama_direct

# Pre-configure LiteLLM
litellm.telemetry = False
litellm.set_verbose = False
os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
os.environ["LITELLM_LOG"] = "WARNING"

# Purge any StreamHandlers LiteLLM added during import across all LiteLLM loggers
sync_litellm_loggers()


def generate(
    system_prompt: str,
    user_message: str,
    config_or_subconfig: Dict[str, Any],
    llm_config: Optional[Dict[str, Any]] = None,
    tools: Optional[List[Dict[str, Any]]] = None,
    stream: bool = False,
    images: Optional[List[Any]] = None,
    extra_messages: Optional[List[Dict[str, Any]]] = None,
) -> Any:
    """
    Generates a response using LiteLLM (cloud/kobold) or direct Ollama runner.
    - images: optional list of dicts {data: bytes, mime_type: str, name: str}
    - extra_messages: optional list of dict objects for the agentic loop.
    """
    params, backend_type, model_name, provider, specific_config = build_llm_params(
        system_prompt=system_prompt,
        user_message=user_message,
        config_or_subconfig=config_or_subconfig,
        llm_config=llm_config,
        tools=tools,
        stream=stream,
        images=images,
        extra_messages=extra_messages,
    )

    if not params or not model_name:
        return "[SYSTEM] Error: Model not found."

    debug_enabled = llm_config.get('debug_llm', False) if llm_config else False

    # Log payload metrics and dump debug logs if enabled
    analyze_and_record_payload(params, model_name, backend_type, specific_config)
    if debug_enabled:
        zlog_info("LiteLLM", f"Debug Activated for: {model_name}")
        safe_params = {k: v for k, v in params.items() if k not in ['api_key', 'tools', 'messages']}
        zlog_debug("LiteLLM", f"REQUEST_PARAMS (Metadata): {json.dumps(safe_params, indent=2)}")
        dump_debug_payload(params, model_name)

    # ── Retry loop with key failover ─────────────────────────────────────────
    from hecos.core.keys import get_key_manager as _get_km
    try:
        import hecos.core.keys.key_manager as _km_settings
        _max_key_retries = getattr(_km_settings, "_KM_MAX_RETRIES", 5)
        try:
            _pool_size = len(_get_km()._pools.get(provider.lower(), [])) if provider else 0
            _max_key_retries = max(_max_key_retries, _pool_size)
        except Exception:
            pass
    except Exception:
        _max_key_retries = 5

    _tried_keys: List[str] = []

    for _attempt in range(_max_key_retries):
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
                zlog_info("LiteLLM", f"[FAILOVER] Switching to key #{_attempt + 1} for '{provider}' ({masked2})")
            except Exception:
                break

        _used_key = params.get("api_key", None)
        if _used_key:
            _tried_keys.append(_used_key)

        try:
            # Route A: Direct Ollama (captures reasoning field and avoids dropped tools)
            if backend_type == "ollama" and not stream:
                return execute_ollama_direct(params, stream=False)

            # Route B: Standard LiteLLM completion
            response = litellm.completion(**params)
            if stream:
                return response

            usage = getattr(response, "usage", None)
            if usage:
                update_usage_telemetry(usage)

            choice = response.choices[0]
            msg = choice.message
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                if debug_enabled:
                    zlog_debug("LiteLLM", f"TOOL_CALLS: {msg.tool_calls}")
                return msg

            if debug_enabled:
                zlog_debug("LiteLLM", f"RESPONSE_OBJECT: {str(response)[:2000]}")

            if not msg.content:
                _thinking = (
                    getattr(msg, 'reasoning_content', None) or
                    getattr(msg, 'thinking', None) or
                    getattr(msg, 'reasoning', None) or
                    ""
                )
                if _thinking:
                    zlog_debug("LiteLLM", f"Thinking model detected: content empty but reasoning found ({len(_thinking)} chars)")
                    return f"<think>{_thinking}</think>"

                if getattr(choice, 'finish_reason', None) == 'content_filter' or getattr(response, 'prompt_feedback', {}).get('blockReason'):
                    zlog_error("LiteLLM: Response BLOCKED by safety filter.")
                    return "!!!BLOCK_SAFETY!!!"
                return ""

            content = msg.content.strip()
            content = re.sub(r'^(HECOS|Hecos|hecos)\s*:\s*', '', content, flags=re.IGNORECASE)
            return content

        except Exception as e:
            error_msg = str(e)
            error_type = type(e).__name__
            zlog_error(f"LiteLLM: [{error_type}] Error (attempt {_attempt + 1}/{_max_key_retries}) with model '{model_name}': {error_msg}")

            if "Timeout" in error_type or "timeout" in error_msg.lower():
                zlog_error(f"LiteLLM: TIMEOUT on attempt {_attempt + 1}! Provider='{provider}', Model='{model_name}'.")
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
                except Exception:
                    pass

            if "401" in error_msg or "403" in error_msg or "429" in error_msg:
                continue

            if backend_type == "ollama" and ("Connection" in error_type or "ConnectError" in error_type or "connection refused" in error_msg.lower() or "target machine actively refused it" in error_msg.lower()):
                _url = params.get("api_base", "http://localhost:11434")
                return (
                    f"⚠️ **Ollama Connection Failed**\n"
                    f"Hecos cannot connect to the Ollama service at `{_url}`.\n\n"
                    f"**Please verify that:**\n"
                    f"1. Ollama is installed on your system.\n"
                    f"2. The Ollama application is currently open and running.\n"
                    f"3. You have pulled at least one model (e.g., run `ollama run qwen3.5` in your terminal)."
                )

            if "400" in error_msg:
                return f"⚠️ Error 400: Invalid parameters for '{model_name}'. Details: {error_msg[:200]}"
            if "404" in error_msg:
                return f"⚠️ Error 404: The model '{model_name}' was not found or the endpoint is incorrect."
            if "503" in error_msg or "ServiceUnavailableError" in error_msg:
                return f"⚠️ AI Server Overloaded (Error 503). Provider {provider} is temporarily unavailable. Details: {error_msg[:100]}"
            return f"⚠️ Unexpected LLM Error [{error_type}]: {error_msg[:250]}"

    return f"⚠️ All API keys for '{provider}' are exhausted or invalid. Please add new keys in the Key Manager."
