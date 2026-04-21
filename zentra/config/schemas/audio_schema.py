"""
MODULE: Audio Config Schema
DESCRIPTION: Pydantic v2 model for config/audio.yaml
"""

from pydantic import BaseModel


class PttSources(BaseModel):
    """Toggleable PTT input sources for the PTT Bus."""
    keyboard_hotkey:  bool = True    # Ctrl+Shift (configurable via ptt_hotkey)
    media_play_pause: bool = False   # BT headset media Play-Pause key (VK 179)
    watch_button:     bool = False   # Smartwatch HID: sends CTRL_L hold-to-talk
    webhook:          bool = False   # HTTP /api/remote-triggers/ptt/*
    custom_key:       bool = False   # Arbitrary key defined by custom_ptt_key

class AudioConfig(BaseModel):
    """Root schema for config/audio.yaml"""

    # --- Device ---
    output_device_index: int = -1
    output_device_name: str = ""
    input_device_index: int = -1
    input_device_name: str = ""
    auto_select: bool = True
    test_on_startup: bool = True
    fallback_on_error: bool = True
    beep_on_select: bool = True
    last_scan: str = ""

    # --- TTS (Piper) ---
    voice_status: bool = True
    piper_path: str = "C:/piper/piper.exe"
    onnx_model: str = "C:/piper/it_IT-paola-medium.onnx"
    speed: float = 1.2
    noise_scale: float = 0.817
    noise_w: float = 0.9
    sentence_silence: float = 0.1

    # --- STT / Listening ---
    listening_status: bool = False
    energy_threshold: int = 450
    silence_timeout: int = 5
    phrase_limit: int = 15
    push_to_talk: bool = False
    ptt_hotkey: str = "ctrl+shift"
    stt_source: str = "web"      # 'system' | 'web'
    tts_destination: str = "web" # 'system' | 'web'
    audio_mode: str = "console"  # 'console' | 'web' | 'auto'

    # --- PTT Sources ---
    ptt_sources:    PttSources = PttSources()
    custom_ptt_key: str = ""           # e.g. "f8" or "ctrl+alt+space"
