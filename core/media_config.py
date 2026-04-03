import json
import os
from core.logging import logger

_PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
MEDIA_CONFIG_PATH = os.path.join(_PROJECT_ROOT, "config", "media.json")

def _get_default_media_config():
    return {
        "image_gen": {
            "enabled": True,
            "provider": "pollinations",
            "model": "flux",
            "width": 1024,
            "height": 1024,
            "nologo": True,
            "api_key": ""
        },
        "video_gen": {
            "enabled": False
        }
    }

def get_media_config():
    if not os.path.exists(MEDIA_CONFIG_PATH):
        cfg = _get_default_media_config()
        save_media_config(cfg)
        return cfg
    try:
        with open(MEDIA_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Ensure base objects exist for backward/forward compatibility
            defaults = _get_default_media_config()
            for k, v in defaults.items():
                if k not in data:
                    data[k] = v
                elif isinstance(v, dict):
                    for sub_k, sub_v in v.items():
                        if sub_k not in data[k]:
                            data[k][sub_k] = sub_v
            return data
    except Exception as e:
        logger.error(f"[MEDIA CONFIG] Error loading {MEDIA_CONFIG_PATH}: {e}")
        return _get_default_media_config()

def save_media_config(cfg):
    try:
        with open(MEDIA_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4)
        return True
    except Exception as e:
        logger.error(f"[MEDIA CONFIG] Error saving {MEDIA_CONFIG_PATH}: {e}")
        return False
