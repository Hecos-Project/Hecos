"""
MODULE: core/llm/vision/factory.py
PURPOSE: Factory that selects the correct VisionAdapter based on model/backend.

Usage:
    from zentra.core.llm.vision.factory import get_vision_adapter
    adapter = get_vision_adapter(model_name, backend_type)
    if adapter:
        messages = adapter.build_messages(system_prompt, user_text, images)
"""

from zentra.core.logging.logger import debug as zlog_debug, error as zlog_error


# ── Provider prefix → adapter mapping ─────────────────────────────
_PROVIDER_MAP = {
    "gemini":    "gemini",
    "openai":    "openai",
    "groq":      "openai",    # Groq is OpenAI-compatible; vision depends on model
    "anthropic": None,        # Claude vision uses a different SDK - TODO
    "ollama":    "ollama",
}


def get_vision_adapter(model_name: str, backend_type: str):
    """
    Return the appropriate VisionAdapter instance, or None if vision is not supported.

    Args:
        model_name:   Full model name, e.g. 'gemini/gemini-1.5-pro' or 'llava'
        backend_type: 'cloud', 'ollama', 'kobold'
    """
    try:
        # Determine provider from model name prefix
        provider = model_name.split("/")[0].lower() if "/" in model_name else backend_type

        adapter_name = _PROVIDER_MAP.get(provider)

        if adapter_name == "gemini":
            from .gemini_vision import GeminiVisionAdapter
            zlog_debug("VisionFactory", f"Selected GeminiVisionAdapter for '{model_name}'")
            return GeminiVisionAdapter()

        elif adapter_name == "openai":
            from .openai_vision import OpenAIVisionAdapter
            zlog_debug("VisionFactory", f"Selected OpenAIVisionAdapter for '{model_name}'")
            return OpenAIVisionAdapter()

        elif adapter_name == "ollama":
            from .ollama_vision import OllamaVisionAdapter
            zlog_debug("VisionFactory", f"Selected OllamaVisionAdapter for '{model_name}'")
            return OllamaVisionAdapter()

        else:
            zlog_debug("VisionFactory", f"No vision adapter available for provider '{provider}' (model: '{model_name}')")
            return None

    except Exception as e:
        zlog_error(f"VisionFactory: Error selecting adapter: {e}")
        return None
