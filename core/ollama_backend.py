"""
MODULO: Ollama Backend - Aura Core
DESCRIZIONE: Gestisce la comunicazione con il server Ollama.
TUTTI i parametri vengono ESCLUSIVAMENTE dal config.json - nessun valore hardcodato.
"""

import requests
import time
from core import logger

def genera(system_prompt, user_message, config):
    """
    Invia una richiesta a Ollama usando ESCLUSIVAMENTE i parametri del config.json.
    """
    # 1. Recupero parametri
    modello = config.get('modello')
    if not modello:
        logger.errore("[OLLAMA] Modello non definito nel config.json!")
        return "Errore: Modello mancante nel file di configurazione."

    temperature = config.get('temperature')
    if temperature is None:
        logger.errore("[OLLAMA] Temperature non definita nel config.json!")
        return "Errore: Temperature mancante nel file di configurazione."

    num_predict = config.get('num_predict')
    if num_predict is None:
        logger.errore("[OLLAMA] num_predict non definito nel config.json!")
        return "Errore: num_predict mancante nel file di configurazione."

    num_ctx = config.get('num_ctx')
    if num_ctx is None:
        logger.errore("[OLLAMA] num_ctx non definito nel config.json!")
        return "Errore: num_ctx mancante nel file di configurazione."

    num_gpu = config.get('num_gpu')
    if num_gpu is None:
        logger.errore("[OLLAMA] num_gpu non definito nel config.json!")
        return "Errore: num_gpu mancante nel file di configurazione."

    keep_alive = config.get('keep_alive', "5m")
    top_p = config.get('top_p', 0.9)
    repeat_penalty = config.get('repeat_penalty', 1.1)

    # 2. Costruzione del payload
    payload = {
        "model": modello,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        "stream": False,
        "keep_alive": keep_alive,
        "options": {
            "temperature": temperature,
            "num_predict": num_predict,
            "num_ctx": num_ctx,
            "num_gpu": num_gpu,
            "top_p": top_p,
            "repeat_penalty": repeat_penalty
        }
    }

    # 3. Esecuzione della chiamata
    try:
        url = "http://localhost:11434/api/chat"
        logger.info(f"[OLLAMA] Invio richiesta: {modello} | GPU Layers: {num_gpu} | CTX: {num_ctx} | Temp: {temperature}")
        
        start_time = time.time()
        response = requests.post(url, json=payload, timeout=120)
        elapsed = time.time() - start_time

        if response.status_code == 200:
            logger.info(f"[OLLAMA] Risposta generata in {elapsed:.2f}s")
            return response.json().get('message', {}).get('content', '')
        else:
            errore_msg = response.text
            logger.errore(f"[OLLAMA] Errore HTTP {response.status_code}: {errore_msg}")
            return f"[ERRORE OLLAMA] Status {response.status_code}"
            
    except requests.exceptions.Timeout:
        logger.errore("[OLLAMA] Timeout raggiunto.")
        return "[SISTEMA] Errore: Timeout della GPU."
    except Exception as e:
        logger.errore(f"[OLLAMA] Errore critico: {e}")
        return f"[SISTEMA] Errore connessione: {e}"