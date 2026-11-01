"""
hecos/modules/web_ui/vision/config.py
Loads, caches and reloads vision.yaml configuration.
"""
import os
import logging
from typing import Optional

logger = logging.getLogger("hecos.web_ui.vision.config")

_VISION_CFG_CACHE = None


def get_vision_config_path() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    hecos_root = os.path.normpath(os.path.join(here, "..", "..", ".."))
    return os.path.join(hecos_root, "config", "data", "vision.yaml")


def load_vision_config(force_reload: bool = False) -> dict:
    global _VISION_CFG_CACHE
    if _VISION_CFG_CACHE is not None and not force_reload:
        return _VISION_CFG_CACHE

    cfg_path = get_vision_config_path()
    try:
        from hecos.config import load_yaml
        from hecos.config.schemas.vision_schema import VisionConfig
        if os.path.exists(cfg_path):
            model = load_yaml(cfg_path, VisionConfig)
            _VISION_CFG_CACHE = model.model_dump()
        else:
            _VISION_CFG_CACHE = VisionConfig().model_dump()
    except Exception as e:
        logger.warning(f"[VisionConfig] Could not load vision.yaml ({e}), using default schema")
        try:
            from hecos.config.schemas.vision_schema import VisionConfig
            _VISION_CFG_CACHE = VisionConfig().model_dump()
        except Exception:
            _VISION_CFG_CACHE = {
                "enabled": True,
                "max_resolution_px": 512,
                "jpeg_quality": 80,
                "timeout_seconds": 5,
                "bridge": {
                    "enabled": True,
                    "mode": "auto",
                    "cloud_model": "gemini/gemini-2.5-flash",
                    "local_model": "moondream",
                    "inspection_prompt": "Descrivi in dettaglio e in modo oggettivo gli elementi visivi dell'immagine: soggetti, azioni, testo visibile, colori, ambiente e dettagli salienti."
                },
                "net_search": {
                    "verify_results": True,
                    "max_thumbnails": 4
                }
            }

    return _VISION_CFG_CACHE


def reload_vision_config() -> dict:
    return load_vision_config(force_reload=True)

