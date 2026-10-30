"""
hecos/core/audio/tts/kokoro
Modular subsystem for Kokoro TTS voice cloning, custom voice management, and style embeddings.
"""

from .cloner import KokoroCloner
from .voice_manager import KokoroVoiceManager

__all__ = ["KokoroCloner", "KokoroVoiceManager"]
