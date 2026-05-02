"""
MODULE: core/llm/vision/__init__.py
PURPOSE: Package init — exposes the main entry point for vision support.
"""

from .factory import get_vision_adapter
from .base import get_mime_type

__all__ = ["get_vision_adapter", "get_mime_type"]
