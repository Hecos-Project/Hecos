"""
MODULE: Media Config
DESCRIPTION: Loads, validates and saves the media configuration via YAML + Pydantic.
             Auto-migrates from legacy config/media.json on first run.
"""

import os
from hecos.core.logging import logger
from hecos.config.yaml_utils import load_yaml, save_yaml
from hecos.config.schemas.media_schema import MediaConfig

# hecos/core -> hecos/
_HECOS_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
MEDIA_CONFIG_PATH = os.path.join(_HECOS_DIR, "config", "data", "media.yaml")


def get_media_config() -> dict:
    """Returns the full media configuration as a plain dict."""
    try:
        model = load_yaml(MEDIA_CONFIG_PATH, MediaConfig)
        return model.model_dump()
    except Exception as e:
        logger.error(f"[MEDIA CONFIG] Error loading config: {e}")
        return MediaConfig().model_dump()


def save_media_config(cfg: dict) -> bool:
    """Validates cfg against MediaConfig and saves to config/media.yaml."""
    try:
        model = MediaConfig.model_validate(cfg)
        return save_yaml(MEDIA_CONFIG_PATH, model)
    except Exception as e:
        logger.error(f"[MEDIA CONFIG] Error saving media config: {e}")
        return False
