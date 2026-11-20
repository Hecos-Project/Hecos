"""
MODULE: core/llm/vision/factory.py
PURPOSE: Factory that selects the correct VisionAdapter based on model/backend.

Usage:
    from hecos.core.llm.vision.factory import get_vision_adapter
    adapter = get_vision_adapter(model_name, backend_type)
    if adapter:
        messages = adapter.build_messages(system_prompt, user_text, images)
"""

from hecos.core.logging.logger import debug as zlog_debug, error as zlog_error


# ── Known Cloud Provider Prefixes ─────────────────────────────────
_KNOWN_CLOUD_PROVIDERS = {
    "gemini":    "gemini",
    "openai":    "openai",
    "groq":      "openai",    # Groq is OpenAI-compatible; vision depends on model
    "anthropic": "openai",    # LiteLLM normalizes Anthropic vision via standard multipart
    "ollama":    "ollama",
}

# Keywords indicating an Ollama model has computer vision capabilities
_OLLAMA_VISION_KEYWORDS = [
    "vision", "vl", "llava", "moondream", "minicpm", "cogvlm",
    "bakllava", "pixtral", "internvl", "obsidian"
]


def get_vision_adapter(model_name: str, backend_type: str):
    """
    Return the appropriate VisionAdapter instance, or None if vision is not supported natively.

    Args:
        model_name:   Full model name, e.g. 'gemini/gemini-2.5-flash', 'masska129/gemma-4-abliterated', 'llava:7b'
        backend_type: 'cloud', 'ollama', 'kobold', 'llama_cpp'
    """
    if not model_name:
        return None

    try:
        m_lower = model_name.lower().strip()
        b_lower = (backend_type or "").lower().strip()

        # 1. First check if explicit cloud prefix is present (e.g. gemini/..., openai/...)
        prefix = m_lower.split("/")[0] if "/" in m_lower else ""
        resolved_provider = None

        if prefix in _KNOWN_CLOUD_PROVIDERS:
            resolved_provider = _KNOWN_CLOUD_PROVIDERS[prefix]
        elif b_lower == "ollama" or m_lower.startswith("ollama/"):
            resolved_provider = "ollama"
        elif "gemini" in m_lower:
            resolved_provider = "gemini"
        elif "gpt-4" in m_lower or "o1" in m_lower or "o3" in m_lower:
            resolved_provider = "openai"
        elif b_lower in ("cloud", "hybrid"):
            # Check model name keywords
            if "claude" in m_lower:
                resolved_provider = "openai"
            elif "gemini" in m_lower:
                resolved_provider = "gemini"
            else:
                resolved_provider = "openai"

        # 2. Provider-specific handling
        if resolved_provider == "gemini":
            from .gemini_vision import GeminiVisionAdapter
            zlog_debug("VisionFactory", f"Selected GeminiVisionAdapter for '{model_name}'")
            return GeminiVisionAdapter()

        elif resolved_provider == "openai":
            from .openai_vision import OpenAIVisionAdapter
            zlog_debug("VisionFactory", f"Selected OpenAIVisionAdapter for '{model_name}'")
            return OpenAIVisionAdapter()

        elif resolved_provider == "ollama":
            # Check if this local Ollama model actually possesses vision weights
            has_vision = any(vk in m_lower for vk in _OLLAMA_VISION_KEYWORDS)
            if not has_vision:
                zlog_debug(
                    "VisionFactory",
                    f"Ollama model '{model_name}' is text-only (no vision weights) — native vision adapter skipped."
                )
                return None

            from .ollama_vision import OllamaVisionAdapter
            zlog_debug("VisionFactory", f"Selected OllamaVisionAdapter for '{model_name}'")
            return OllamaVisionAdapter()

        else:
            zlog_debug("VisionFactory", f"No native vision adapter for model '{model_name}' (backend: '{backend_type}')")
            return None

    except Exception as e:
        zlog_error(f"VisionFactory: Error selecting adapter: {e}")
        return None
