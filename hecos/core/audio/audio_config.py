"""
MODULE: Audio Config
DESCRIPTION: Loads, validates and saves the audio configuration via YAML + Pydantic.
             Auto-migrates from legacy config/audio.json on first run.
"""

import os as _os
from hecos.config.yaml_utils import load_yaml, save_yaml
from hecos.config.schemas.audio_schema import AudioConfig

# --- Constants ---
# hecos/core/audio -> hecos/
_HECOS_DIR = _os.path.normpath(_os.path.join(_os.path.dirname(__file__), "..", ".."))
CONFIG_AUDIO_PATH = _os.path.join(_HECOS_DIR, "config", "data", "audio.yaml")

# ──────────────────────────────────────────────────────────────────────────────
# CONFIG I/O
# ──────────────────────────────────────────────────────────────────────────────

def _load_audio_config() -> dict:
    """Loads config/audio.yaml (auto-migrating from audio.json if needed)."""
    model = load_yaml(CONFIG_AUDIO_PATH, AudioConfig)
    return model.model_dump()


def _save_audio_config(cfg: dict) -> bool:
    """Validates cfg against AudioConfig and saves to config/audio.yaml."""
    try:
        from datetime import datetime
        if not cfg.get("last_scan"):
            cfg["last_scan"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        model = AudioConfig.model_validate(cfg)
        return save_yaml(CONFIG_AUDIO_PATH, model)
    except Exception as e:
        print(f"[AUDIO-DM] Save error: {e}")
        return False


# ──────────────────────────────────────────────────────────────────────────────
# PUBLIC GETTERS / SETTERS (same API as before)
# ──────────────────────────────────────────────────────────────────────────────

def get_audio_config() -> dict:
    """Returns the full audio configuration dict."""
    return _load_audio_config()

# ──────────────────────────────────────────────────────────────────────────────
# BACKWARD COMPAT STUBS
# device_manager.py imports these by name — kept as no-ops / aliases.
# ──────────────────────────────────────────────────────────────────────────────

def _migrate_from_main_config():
    """
    Legacy stub — migration from system.json to audio.yaml is now handled
    automatically by yaml_utils.load_yaml() on first import.
    Kept here for backward compatibility with device_manager.py.
    """
    pass
