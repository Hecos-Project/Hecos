import os
import json
from core.logging import logger

GREETINGS_FILE = os.path.join("assets", "voice_greetings.json")

DEFAULT_GREETINGS = {
    "en": "Hello, I am Zentra.",
    "it": "Sistemi operativi Zentra, Avviati.",
    "es": "Hola, soy Zentra.",
    "fr": "Bonjour, je suis Zentra.",
    "de": "Hallo, ich bin Zentra.",
    "fallback": "System Ready."
}

def get_spoken_greeting(config=None):
    """
    Returns the appropriate spoken greeting based on the loaded TTS voice language.
    If the JSON file does not exist, it will be automatically generated with defaults.
    """
    # 1. Determina la lingua del modello vocale (es. "it_IT-paola..." -> "it")
    # UPDATED: Legge da config_audio.json invece che dal config globale passato
    try:
        from core.audio.device_manager import get_audio_config
        audio_cfg = get_audio_config()
        onnx_model = os.path.basename(audio_cfg.get("onnx_model", "en_US-lessac.onnx"))
    except Exception as e:
        logger.debug("SYSTEM", f"Errore lettura config audio in greeting: {e}")
        # Fallback al vecchio metodo se presente nel config
        onnx_model = os.path.basename(config.get("voice", {}).get("onnx_model", "en_US-lessac.onnx")) if config else "en_US-lessac.onnx"
    
    voice_language = onnx_model.split("_")[0] if "_" in onnx_model else "en"
    
    # 2. Carica o crea il file JSON
    if not os.path.exists(GREETINGS_FILE):
        try:
            os.makedirs(os.path.dirname(GREETINGS_FILE), exist_ok=True)
            with open(GREETINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_GREETINGS, f, indent=4, ensure_ascii=False)
            logger.info("SYSTEM", f"Creato file custom per frasi vocali: {GREETINGS_FILE}")
            greetings = DEFAULT_GREETINGS
        except Exception as e:
            logger.warning("SYSTEM", f"Impossibile salvare voice_greetings.json: {e}")
            greetings = DEFAULT_GREETINGS
    else:
        try:
            with open(GREETINGS_FILE, "r", encoding="utf-8") as f:
                greetings = json.load(f)
        except Exception as e:
            logger.warning("SYSTEM", f"Impossibile leggere {GREETINGS_FILE}: {e}")
            greetings = DEFAULT_GREETINGS
            
    # 3. Restituisci la stringa appropriata per quella lingua, o il fallback
    return greetings.get(voice_language, greetings.get("fallback", "System Ready."))
