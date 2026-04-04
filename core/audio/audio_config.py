"""
MODULE: Audio Config
DESCRIPTION: Loads, validates and saves the audio configuration via YAML + Pydantic.
             Auto-migrates from legacy config/audio.json on first run.
"""

import os as _os
from config.yaml_utils import load_yaml, save_yaml
from config.schemas.audio_schema import AudioConfig

# --- Constants ---
_PROJECT_ROOT = _os.path.normpath(_os.path.join(_os.path.dirname(__file__), "..", ".."))
CONFIG_AUDIO_PATH = _os.path.join(_PROJECT_ROOT, "config", "audio.yaml")

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

def get_output_device() -> int:
    """Returns the configured output device index (-1 = system default)."""
    cfg = _load_audio_config()
    return cfg.get("output_device_index", -1)


def get_input_device():
    """Returns the configured input device index (None = system default)."""
    cfg = _load_audio_config()
    idx = cfg.get("input_device_index", -1)
    return idx if idx >= 0 else None


def get_audio_config() -> dict:
    """Returns the full audio configuration dict."""
    return _load_audio_config()


def set_output_device(index: int, name: str = "") -> bool:
    """Manually sets the output device and saves."""
    cfg = _load_audio_config()
    cfg["output_device_index"] = index
    cfg["output_device_name"] = name
    cfg["auto_select"] = False
    return _save_audio_config(cfg)


def set_input_device(index: int, name: str = "") -> bool:
    """Manually sets the input device and saves."""
    cfg = _load_audio_config()
    cfg["input_device_index"] = index
    cfg["input_device_name"] = name
    cfg["auto_select"] = False
    return _save_audio_config(cfg)


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
