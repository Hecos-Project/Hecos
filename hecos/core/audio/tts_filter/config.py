import os
import json
from hecos.core.logging import logger

_HECOS_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
FILTER_CONFIG_FILE = os.path.join(_HECOS_DIR, "config", "data", "tts_filters.json")

def get_filter_config() -> dict:
    if os.path.exists(FILTER_CONFIG_FILE):
        try:
            with open(FILTER_CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error("TTS_FILTER", f"Failed to read filter config: {e}")
    
    # Default config
    return {
        "remove_punctuation": False,
        "remove_llm_errors": True,
        "xtts_fix_periods": True,
        "custom_replacements": []
    }

def save_filter_config(data: dict) -> bool:
    try:
        os.makedirs(os.path.dirname(FILTER_CONFIG_FILE), exist_ok=True)
        with open(FILTER_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        return True
    except Exception as e:
        logger.error("TTS_FILTER", f"Failed to save filter config: {e}")
        return False
