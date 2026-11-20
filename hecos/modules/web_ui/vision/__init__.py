"""
hecos/modules/web_ui/vision/
Unified Multimodal Perception Subsystem for Hecos.

Provides:
- Native multimodal dispatch for vision models (Gemini, GPT-4o, LLaVA, etc.)
- Vision Bridge / Sidecar for text-only local models (Gemma, Qwen, etc.)
- Net Search thumbnail extraction and visual verification
- Pillow optimization and Base64 encoding
- Complete UI configuration integration
"""
from .config import load_vision_config, reload_vision_config
from .processor import optimize_image_bytes, bytes_to_b64_dict, fetch_image_from_url
from .inspector import inspect_image
from .router import VisionRouter
from .netsearch_bridge import extract_search_session_images

__all__ = [
    "load_vision_config",
    "reload_vision_config",
    "optimize_image_bytes",
    "bytes_to_b64_dict",
    "fetch_image_from_url",
    "inspect_image",
    "VisionRouter",
    "extract_search_session_images",
]

