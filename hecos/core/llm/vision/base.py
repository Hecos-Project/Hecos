"""
MODULE: core/llm/vision/base.py
PURPOSE: Abstract base class for all vision (multimodal) adapters.
Each backend provider subclasses this and implements `build_messages()`.
"""

from abc import ABC, abstractmethod
import base64
import mimetypes
import os


class VisionAdapter(ABC):
    """
    Abstract adapter for building multimodal message payloads.
    Subclasses implement the specific format required by each LLM provider.
    """

    @abstractmethod
    def build_messages(self, system_prompt: str, user_message: str, images: list[dict]) -> list[dict]:
        """
        Build the messages list to pass to the LLM API.

        Args:
            system_prompt:  The full system prompt string.
            user_message:   The user's text message.
            images:         List of dicts with keys:
                              - 'data': raw bytes of the image
                              - 'mime_type': e.g. 'image/jpeg'
                              - 'name': original filename

        Returns:
            A list of message dicts ready for the LLM API.
        """

    @abstractmethod
    def is_supported(self) -> bool:
        """Return True if this adapter can handle vision for the given model."""


# ── Utility helpers shared across adapters ─────────────────────────
def encode_image_b64(image_bytes: bytes) -> str:
    """Encode raw image bytes to a base64 string."""
    return base64.b64encode(image_bytes).decode("utf-8")


def get_mime_type(filename: str) -> str:
    """Guess MIME type from filename, default to image/jpeg."""
    mime, _ = mimetypes.guess_type(filename)
    return mime or "image/jpeg"
