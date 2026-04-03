"""
MODULE: Audio Config
DESCRIPTION: Handles loading, saving, and migrating audio configurations.
"""

import os
import json
from datetime import datetime

# --- Constants ---
import os as _os
_PROJECT_ROOT = _os.path.normpath(_os.path.join(_os.path.dirname(__file__), "..", ".."))
CONFIG_AUDIO_PATH = _os.path.join(_PROJECT_ROOT, "config", "audio.json")

# ──────────────────────────────────────────────────────────────────────────────
# CONFIG I/O
# ──────────────────────────────────────────────────────────────────────────────

def _load_audio_config() -> dict:
    """Loads config_audio.json, returns defaults if missing."""
    defaults = {
        "output_device_index": -1,
        "output_device_name": "",
        "input_device_index": -1,
        "input_device_name": "",
        "auto_select": True,
        "test_on_startup": True,
        "fallback_on_error": True,
        "beep_on_select": True,
        "last_scan": "",
        
        # --- Voice Settings ---
        "voice_status": True,
        "piper_path": "C:\\piper\\piper.exe",
        "onnx_model": "C:\\piper\\it_IT-aurora-medium.onnx",
        "speed": 1.2,
        "noise_scale": 0.817,
        "noise_w": 0.9,
        "sentence_silence": 0.1,
        
        # --- Listening Settings ---
        "listening_status": True,
        "energy_threshold": 450,
        "silence_timeout": 5,
        "phrase_limit": 15,
        "push_to_talk": False,
        "ptt_hotkey": "ctrl+shift",
        "stt_source": "system",    # 'system' (PC mic) or 'web' (browser input)
        "tts_destination": "web"   # 'system' (PC speakers) or 'web' (browser audio)
    }
    try:
        if os.path.exists(CONFIG_AUDIO_PATH):
            with open(CONFIG_AUDIO_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                defaults.update(data)
    except Exception:
        pass
    return defaults


def _save_audio_config(cfg: dict) -> bool:
    """Saves config_audio.json."""
    try:
        if "last_scan" not in cfg or cfg.get("last_scan") == "":
             cfg["last_scan"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(CONFIG_AUDIO_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"[AUDIO-DM] Save error: {e}")
        return False


def _migrate_from_main_config():
    """Migrates 'voice' and 'listening' dicts from config/system.json to config/audio.json, then deletes them."""
    main_cfg_path = _os.path.join(_PROJECT_ROOT, "config", "system.json")
    if not _os.path.exists(main_cfg_path): return
    
    try:
        with open(main_cfg_path, "r", encoding="utf-8") as f:
            main_data = json.load(f)
            
        has_voice = "voice" in main_data
        has_listening = "listening" in main_data
        
        if not has_voice and not has_listening:
            return # Nothing to migrate
            
        audio_cfg = _load_audio_config()
        
        if has_voice:
            voice_data = main_data.pop("voice")
            if isinstance(voice_data, dict):
                for k, v in voice_data.items():
                    audio_cfg[k] = v
                    
        if has_listening:
            listening_data = main_data.pop("listening")
            if isinstance(listening_data, dict):
                for k, v in listening_data.items():
                    audio_cfg[k] = v
                    
        # Save both
        _save_audio_config(audio_cfg)
        
        with open(main_cfg_path, "w", encoding="utf-8") as f:
            json.dump(main_data, f, indent=4, ensure_ascii=False)
            
        print("[AUDIO-DM] Successfully migrated voice/listening settings to config_audio.json")
    except Exception as e:
        print(f"[AUDIO-DM] Migration error: {e}")

# Run migration early on import if needed
_migrate_from_main_config()


# ──────────────────────────────────────────────────────────────────────────────
# PUBLIC GETTERS (used by voice.py and listen.py)
# ──────────────────────────────────────────────────────────────────────────────

def get_output_device() -> int:
    """
    Returns the configured output device index.
    Returns -1 if not configured or config missing (sounddevice will use system default).
    """
    cfg = _load_audio_config()
    return cfg.get("output_device_index", -1)


def get_input_device() -> int:
    """
    Returns the configured input device index.
    Returns None if not configured (speech_recognition will use system default).
    """
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
    cfg["output_device_name"]  = name
    cfg["auto_select"]         = False
    return _save_audio_config(cfg)


def set_input_device(index: int, name: str = "") -> bool:
    """Manually sets the input device and saves."""
    cfg = _load_audio_config()
    cfg["input_device_index"] = index
    cfg["input_device_name"]  = name
    cfg["auto_select"]         = False
    return _save_audio_config(cfg)
