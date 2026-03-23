"""
MODULO: LiteLLM Client - Zentra Core (MANUAL LOGGING)
DESCRIZIONE: Client unificato per la generazione di testo via LiteLLM con log rincanalati.
"""

import litellm
import os
import json
# Importiamo correttamente le funzioni dal modulo logger
from core.logging import logger as log_mod
from core.logging.logger import debug as zlog_debug, info as zlog_info, errore as zlog_error

# Configurazione globale LiteLLM
litellm.telemetry = False 

def generate(system_prompt, user_message, config_or_subconfig, llm_config=None):
    """
    Genera una risposta usando LiteLLM.
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
        return f"[SYSTEM] Errore: Modello non trovato."

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
        "num_retries": 1 
    }

    # 4. Configurazione Provider
    if backend_type == "ollama":
        if not model_name.startswith("ollama/"):
            params["model"] = f"ollama/{model_name}"
        params["api_base"] = "http://localhost:11434"

    elif backend_type == "kobold":
        if not model_name.startswith("openai/"):
            params["model"] = f"openai/{model_name}"
        params["api_base"] = specific_config.get('url', 'http://localhost:5001').rstrip('/') + "/v1"

    elif backend_type == "cloud":
        actual_model = model_name.split('/', 1)[1] if '/' in model_name else model_name
        
        if llm_config:
            api_key = llm_config.get('providers', {}).get(provider, {}).get('api_key')
            if api_key:
                params["api_key"] = api_key
                params["custom_llm_provider"] = provider
                
                if provider == "gemini":
                    os.environ["GEMINI_API_KEY"] = api_key
                    params["model"] = actual_model
                    
                    if any(v in actual_model for v in ["2.0", "3", "-latest", "-preview", "-exp"]):
                        params["api_base"] = "https://generativelanguage.googleapis.com/v1beta"
                    else:
                        params["api_base"] = "https://generativelanguage.googleapis.com/v1"
                else:
                    params["model"] = f"{provider}/{actual_model}"

        if not params.get("api_key"):
            return f"[SYSTEM] API key mancante per '{provider}'."

    # LOG MANUALE PRE-CHIAMATA
    if debug_enabled:
        zlog_info("LiteLLM", f"Debug Attivato per: {model_name}")
        zlog_debug("LiteLLM", f"REQUEST_PARAMS: {json.dumps({k:v for k,v in params.items() if k != 'api_key'}, indent=2)}")

    try:
        response = litellm.completion(**params)
        
        # LOG MANUALE POST-CHIAMATA
        if debug_enabled:
            # Serializziamo solo il contenuto utile per non intasare troppo il log se enorme
            zlog_debug("LiteLLM", f"RESPONSE_OBJECT: {str(response)[:2000]}")
            
        return response.choices[0].message.content.strip()
    except Exception as e:
        error_msg = str(e)
        zlog_error(f"LiteLLM: Errore: {error_msg}")
        
        if "400" in error_msg:
            return f"[SYSTEM] Errore 400: Parametri non validi per '{model_name}'."
        if "404" in error_msg:
            return f"[SYSTEM] Errore 404: Modello '{model_name}' non trovato."
        if "429" in error_msg:
            return f"[SYSTEM] Quota Esaurita (429). Riprova tra 60 secondi."
            
        return f"[SYSTEM] Errore: {error_msg[:100]}"