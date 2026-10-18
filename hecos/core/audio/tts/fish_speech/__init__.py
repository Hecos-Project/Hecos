"""
Fish Speech TTS package.
Exports parameters resolution, HTTP client, audio processing, and engine facade.
"""

from hecos.core.audio.tts.fish_speech.params import FishSpeechParams, resolve_fish_params, get_project_root
from hecos.core.audio.tts.fish_speech.client import FishSpeechClient, is_ormsgpack_available
from hecos.core.audio.tts.fish_speech.audio import FishSpeechAudio

__all__ = [
    "FishSpeechParams",
    "resolve_fish_params",
    "get_project_root",
    "FishSpeechClient",
    "is_ormsgpack_available",
    "FishSpeechAudio",
]
