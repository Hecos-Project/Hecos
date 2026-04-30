import os
import json
from hecos.core.logging import logger

# hecos/core/system/greeting.py -> ../../ is hecos/
_HECOS_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
GREETINGS_FILE = os.path.join(_HECOS_DIR, "config", "data", "voice_greetings.json")

DEFAULT_GREETINGS = {
    "en": "Hecos. That's me!",
    "it": "Hecos. Molto piacere!",
    "es": "Hola, soy Hecos.",
    "fr": "Bonjour, je suis Hecos.",
    "de": "Hallo, ich bin Hecos.",
    "fallback": "System Ready."
}

def _load_greetings():
    """Carica le frasi dal file JSON o usa i default."""
    if not os.path.exists(GREETINGS_FILE):
        try:
            os.makedirs(os.path.dirname(GREETINGS_FILE), exist_ok=True)
            with open(GREETINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_GREETINGS, f, indent=4, ensure_ascii=False)
            return DEFAULT_GREETINGS
        except:
            return DEFAULT_GREETINGS
    else:
        try:
            with open(GREETINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return DEFAULT_GREETINGS

def get_spoken_greeting(config=None):
    """
    Restituisce il saluto vocale basato sulla lingua del modello Piper caricato.
    """
    try:
        from hecos.core.audio.device_manager import get_audio_config
        audio_cfg = get_audio_config()
        onnx_model = os.path.basename(audio_cfg.get("onnx_model", "en_US-lessac.onnx"))
    except:
        onnx_model = "en_US-lessac.onnx"
    
    voice_language = onnx_model.split("_")[0] if "_" in onnx_model else "en"
    greetings = _load_greetings()
    return greetings.get(voice_language, greetings.get("fallback", "System Ready."))

def get_ui_greeting(config):
    """
    Restituisce il saluto testuale basato sulla lingua di sistema (UI).
    """
    # Prende la lingua dal config principale (es. config['language'])
    sys_lang = config.get("language", "en") if config else "en"
    greetings = _load_greetings()
    return greetings.get(sys_lang, greetings.get("fallback", "System Ready."))
