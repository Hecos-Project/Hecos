"""
MODULO: LiteLLM Client - Zentra Core (MANUAL LOGGING)
DESCRIZIONE: Client unificato per la generazione di testo via LiteLLM con log rincanalati.
"""

import litellm
import os
import json
import logging
# Importiamo correttamente le funzioni dal modulo logger
from core.logging import logger as log_mod
from core.logging.logger import debug as zlog_debug, info as zlog_info, errore as zlog_error

# Configurazione globale LiteLLM
litellm.telemetry = False

# CRITICAL: Purge any StreamHandlers LiteLLM added during import (they write to stdout/chat)
# LiteLLM may auto-attach a stdout handler if LITELLM_LOG env var is set at import time
_litellm_logger = logging.getLogger("LiteLLM")
for _h in _litellm_logger.handlers[:]:
    if isinstance(_h, logging.StreamHandler) and not isinstance(_h, logging.FileHandler):
        _litellm_logger.removeHandler(_h)
# Ensure LITELLM_LOG doesn't force verbose stdout output
os.environ["LITELLM_LOG"] = ""

def generate(system_prompt, user_message, config_or_subconfig, llm_config=None, tools=None, stream=False):
    """
    Genera una risposta usando LiteLLM, con supporto Opzionale per i Tools e Streaming.
    """
    
    # 1. Identificazione Backend e Modello
    if 'backend' in config_or_subconfig:
        backend_info = config_or_subconfig.get('backend', {})
        backend_type = backend_info.get('tipo', 'ollama')
        specific_config = backend_info.get(backend_type, {})
    else:
        specific_config = config_or_subconfig
        backend_type = specific_config.get('tipo_backend', 'ollama')

    model_name = specific_config.get('modello')
    
    if not model_name:
        return f"[SYSTEM] Error: Model not found."

    # 2. Configurazione Debug
    debug_enabled = llm_config.get('debug_llm', False) if llm_config else False
    
    # Prep di LiteLLM (niente print in chat)
    litellm.set_verbose = False
    
    # 3. Preparazione Messaggi
    provider = model_name.split('/')[0] if '/' in model_name else ""
    
    if provider == "gemini":
        messages = [
            {"role": "user", "content": f"{system_prompt}\n\n[USER]: {user_message}"}
        ]
    else:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

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
        actual_model = model_name.split('/', 1)[1] if '/' in model_name else model_name
        
        # Indica a LiteLLM il provider (es. 'groq', 'openai', 'anthropic', 'gemini')
        params["custom_llm_provider"] = provider
        
        # Mappa dei nomi di variabili d'ambiente per provider
        ENV_KEY_MAP = {
            "groq": "GROQ_API_KEY",
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "gemini": "GEMINI_API_KEY",
            "cohere": "COHERE_API_KEY",
        }
        
        if llm_config:
            # 1. Prova a recuperare la chiave dal config.json
            api_key = llm_config.get('providers', {}).get(provider, {}).get('api_key', '').strip()
            
            # 2. Se assente o vuota, prova la variabile d'ambiente del sistema operativo
            if not api_key:
                env_var = ENV_KEY_MAP.get(provider, f"{provider.upper()}_API_KEY")
                api_key = os.environ.get(env_var, '').strip().strip("'").strip('"')
                if api_key:
                    zlog_info("LiteLLM", f"API key for '{provider}' loaded from environment variable '{env_var}' (starts with: {api_key[:5]}...).")
                else:
                    zlog_debug("LiteLLM", f"API key for '{provider}' not found in environment ({env_var}).")
            else:
                api_key = api_key.strip().strip("'").strip('"')
                zlog_debug("LiteLLM", f"API key for '{provider}' loaded from config.json (starts with: {api_key[:5]}...).")
            
            if api_key:
                params["api_key"] = api_key
                
                if provider == "gemini":
                    os.environ["GEMINI_API_KEY"] = api_key
                    params["model"] = actual_model
                    
                    if any(v in actual_model for v in ["2.0", "3", "-latest", "-preview", "-exp"]):
                        params["api_base"] = "https://generativelanguage.googleapis.com/v1beta"
                    else:
                        params["api_base"] = "https://generativelanguage.googleapis.com/v1"
                else:
                    params["model"] = f"{provider}/{actual_model}"
            else:
                # Nessuna chiave trovata: imposta il modello e lascia LiteLLM gestire l'autenticazione
                zlog_error(f"LiteLLM: No API key found for provider '{provider}' in config or environment. Call may fail.")
                params["model"] = f"{provider}/{actual_model}" if provider else actual_model

    # LOG MANUALE PRE-CHIAMATA
    if debug_enabled:
        zlog_info("LiteLLM", f"Debug Activated for: {model_name}")
        zlog_debug("LiteLLM", f"REQUEST_PARAMS: {json.dumps({k:v for k,v in params.items() if k not in ['api_key', 'tools']}, indent=2)}")

    try:
        response = litellm.completion(**params)

        if stream:
            return response  # Restituisce il generatore per il bridge WebUI

        # CONTROLLO SE HA USATO TOOLS
        msg = response.choices[0].message
        if hasattr(msg, 'tool_calls') and msg.tool_calls:
            if debug_enabled:
                zlog_debug("LiteLLM", f"TOOL_CALLS: {msg.tool_calls}")
            # Ritorna l'oggetto message intero affinché processore.py possa leggerne i tool_calls
            return msg

        # LOG MANUALE POST-CHIAMATA
        if debug_enabled:
            # Serializziamo solo il contenuto utile per non intasare troppo il log se enorme
            zlog_debug("LiteLLM", f"RESPONSE_OBJECT: {str(response)[:2000]}")
            
        return msg.content.strip() if msg.content else ""
    except Exception as e:
        error_msg = str(e)
        zlog_error(f"LiteLLM: Error: {error_msg}")
        
        if "400" in error_msg:
            return f"[SYSTEM] Error 400: Invalid parameters for '{model_name}'."
        if "404" in error_msg:
            return f"[SYSTEM] Error 404: Model '{model_name}' not found."
        if "429" in error_msg:
            return f"[SYSTEM] Quota Exhausted (429). Try again in 60 seconds."
            
        return f"[SYSTEM] Error: {error_msg[:100]}"