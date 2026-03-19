"""
MODULO: Kobold Backend - Aura Core
DESCRIZIONE: Gestisce la comunicazione con KoboldCPP.
"""

import requests
import json
import time
from core import logger

def genera(system_prompt, user_message, config):
    """
    Invia una richiesta a KoboldCPP e restituisce la risposta.
    config: dizionario con parametri (url, modello, temperatura, ...)
    """
    url_base = config.get('url', 'http://localhost:5001').rstrip('/')
    modello = config.get('modello', '')  # non sempre usato, ma per logging
    temperature = config.get('temperature', 0.8)
    max_length = config.get('max_length', 512)
    top_p = config.get('top_p', 0.92)
    rep_pen = config.get('rep_pen', 1.1)

    # Costruisci il prompt completo
    full_prompt = f"{system_prompt}\n\nUtente: {user_message}\nAura:"

    payload = {
        "prompt": full_prompt,
        "max_length": max_length,
        "temperature": temperature,
        "top_p": top_p,
        "rep_pen": rep_pen,
        "stop_sequence": ["Utente:", "Aura:"]
    }

    try:
        url = f"{url_base}/api/v1/generate"
        logger.info(f"[KOBOLD] Invio richiesta a {url_base}...")
        start = time.time()
        response = requests.post(url, json=payload, timeout=240)
        elapsed = time.time() - start

        if response.status_code == 200:
            logger.info(f"[KOBOLD] Risposta in {elapsed:.2f}s")
            risposta = response.json()['results'][0]['text'].strip()
            return risposta
        else:
            logger.errore(f"[KOBOLD] Errore HTTP {response.status_code}")
            return f"[ERRORE KOBOLD] Status {response.status_code}"
    except requests.exceptions.Timeout:
        logger.errore("[KOBOLD] Timeout")
        return "[SISTEMA] Timeout KoboldCPP"
    except requests.exceptions.ConnectionError:
        logger.errore("[KOBOLD] Connessione rifiutata")
        return "[SISTEMA] KoboldCPP non attivo. Avvia KoboldCPP e riprova."
    except Exception as e:
        logger.errore(f"[KOBOLD] Errore: {e}")
        return f"[SISTEMA] Errore KoboldCPP: {e}"