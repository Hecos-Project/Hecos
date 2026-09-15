"""
MODULE: Base TTS Engine
DESCRIPTION: Abstract base class defining the interface for all Hecos TTS engines.
"""

from abc import ABC, abstractmethod

class BaseTTSEngine(ABC):
    @abstractmethod
    def generate_wav(self, text: str, filepath: str, **kwargs) -> bool:
        """
        Synthesizes text and saves it as a single WAV file at `filepath`.
        Returns True on success, False otherwise.
        """
        pass

    @abstractmethod
    def generate_wav_chunked(self, text: str, filepath: str, progress_callback=None, **kwargs) -> bool:
        """
        Splits long text into sentences, synthesizes them individually, 
        and merges them into a single WAV file at `filepath`.
        Returns True on success, False otherwise.
        """
        pass

    @abstractmethod
    def speak(self, text: str, state=None, _run_id=None, _timeout=0, _start=0, **kwargs):
        """
        Synthesizes and immediately plays the text on the local PC speakers.
        Supports cancellation and interruption.
        """
        pass

    @abstractmethod
    def stop(self):
        """
        Immediately halts any ongoing synthesis or playback for this engine.
        """
        pass

    @abstractmethod
    def get_available_voices(self) -> dict:
        """
        Returns a dictionary of available voices for this engine.
        Format: {"voice_id": "Friendly Name", ...}
        """
        pass
