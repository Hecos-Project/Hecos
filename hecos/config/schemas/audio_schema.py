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

class KokoroConfig(BaseModel):
    speed: float = 1.0
    voice: str = "af_heart"   # Default kokoro voice ID
    sentence_silence: float = 0.0 # Pause in seconds between chunks
    model_path: str = ""      # Optional offline model path
    volume: float = 1.0       # Audio output volume factor / gain (0.5 - 2.0)
    normalize: bool = True    # Loudness normalization to match broadcast / system levels

class XttsConfig(BaseModel):
    speed: float = 1.0
    language: str = "it"
    speaker: str = "Claribel Dervla"  # Default XTTS speaker name
    gpu_acceleration: str = "auto"    # 'auto', 'cpu', 'gpu'
    chunk_sentences: bool = True
    speaker_wav: str = ""             # Optional WAV path for voice cloning
    temperature: float = 0.75
    repetition_penalty: float = 5.0
    top_k: int = 50
    top_p: float = 0.85
    length_penalty: float = 1.0
    current_preset: str = "default"

class FishSpeechConfig(BaseModel):
    api_url: str = "http://127.0.0.1:8080/v1/tts"
    api_key: str = ""
    reference_id: str = ""            # Local folder in references/ or Fish Audio cloud model ID
    reference_audio: str = ""         # Path or filename in assets/voice_clones
    reference_text: str = ""          # Transcript of reference audio
    temperature: float = 0.7
    top_p: float = 0.7
    repetition_penalty: float = 1.2
    max_new_tokens: int = 1024
    chunk_length: int = 200           # Iterative prompt window length (100 - 300)
    seed: int = 0                     # 0 = random, >0 = deterministic
    normalize: bool = True            # Text normalization
    use_memory_cache: bool = True     # In-memory VQ-GAN cache for fast repeat inference
    chunk_sentences: bool = True
    current_preset: str = "default"
    current_inference_preset: str = ""
    model_checkpoint: str = "s2-pro"  # Subfolder in hecos/engines/fish_speech/checkpoints/
    volume: float = 1.0               # Audio output loudness normalization and volume factor

class AudioConfig(BaseModel):
    """Root schema for config/audio.yaml"""

    # --- TTS Engine Routing ---
    active_engine: str = "piper"  # 'piper', 'kokoro', 'xtts2', 'fish_speech'
    
    # --- TTS (Piper) ---
    voice_status: bool = True
    piper_path: str = "C:/piper/piper.exe"
    onnx_model: str = "C:/piper/it_IT-paola-medium.onnx"
    speed: float = 1.2
    noise_scale: float = 0.817
    noise_w: float = 0.9
    sentence_silence: float = 0.1
    piper_timeout: int = 180

    # --- TTS (Kokoro) ---
    kokoro: KokoroConfig = KokoroConfig()
    
    # --- TTS (XTTS2) ---
    xtts: XttsConfig = XttsConfig()
    xtts_presets: dict = {}
    xtts_inference_presets: dict = {
        "Fast & Direct": {"speed": 1.4, "temperature": 0.6, "repetition_penalty": 4.0, "top_k": 40, "top_p": 0.8, "length_penalty": 0.9},
        "Expressive & Dynamic": {"speed": 1.0, "temperature": 0.9, "repetition_penalty": 6.0, "top_k": 70, "top_p": 0.9, "length_penalty": 1.2},
        "Slow & Clear": {"speed": 0.8, "temperature": 0.4, "repetition_penalty": 3.0, "top_k": 30, "top_p": 0.7, "length_penalty": 0.8},
        "Creative & Wild": {"speed": 1.1, "temperature": 1.2, "repetition_penalty": 8.0, "top_k": 90, "top_p": 0.95, "length_penalty": 1.5},
        "Stable & Monotone": {"speed": 1.0, "temperature": 0.1, "repetition_penalty": 10.0, "top_k": 10, "top_p": 0.5, "length_penalty": 1.0}
    }

    # --- TTS (Fish Speech) ---
    fish_speech: FishSpeechConfig = FishSpeechConfig()
    fish_speech_presets: dict = {}
    fish_speech_inference_presets: dict = {
        "Standard & Balanced": {"temperature": 0.7, "top_p": 0.7, "repetition_penalty": 1.2, "max_new_tokens": 512, "chunk_length": 200, "normalize": True, "use_memory_cache": True},
        "Expressive & Dynamic": {"temperature": 0.75, "top_p": 0.8, "repetition_penalty": 1.25, "max_new_tokens": 512, "chunk_length": 220, "normalize": True, "use_memory_cache": True},
        "Fast & Direct": {"temperature": 0.5, "top_p": 0.6, "repetition_penalty": 1.15, "max_new_tokens": 384, "chunk_length": 160, "normalize": True, "use_memory_cache": True},
        "Creative & Wild": {"temperature": 0.75, "top_p": 0.8, "repetition_penalty": 1.25, "max_new_tokens": 512, "chunk_length": 220, "normalize": True, "use_memory_cache": True},
        "Stable & Monotone": {"temperature": 0.4, "top_p": 0.5, "repetition_penalty": 1.3, "max_new_tokens": 512, "chunk_length": 200, "normalize": True, "use_memory_cache": True}
    }

    # --- STT / Listening ---
    listening_status: bool = False
    energy_threshold: int = 450
    silence_timeout: int = 5
    phrase_limit: int = 15
    push_to_talk: bool = False
    ptt_hotkey: str = "ctrl+shift"

    # --- PTT Sources ---
    ptt_sources:    PttSources = PttSources()
    custom_ptt_key: str = ""           # e.g. "f8" or "ctrl+alt+space"

    # --- TTS Audio History & Cache ---
    tts_history_max_files: int = 100   # Max WAV files to keep in media/audio/history/
    tts_cache_enabled: bool = True     # Persistent cache for synthesized TTS audio
    tts_cache_max_mb: int = 500        # Maximum size in MB for TTS cache folder
