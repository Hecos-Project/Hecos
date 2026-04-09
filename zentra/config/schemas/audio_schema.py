"""
MODULE: Audio Config Schema
DESCRIPTION: Pydantic v2 model for config/audio.yaml
"""

from pydantic import BaseModel


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
