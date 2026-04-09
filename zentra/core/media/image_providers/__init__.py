"""
core.media.image_providers
Multi-provider image generation engine for Zentra Core.
"""

import os

try:
    from zentra.core.logging import logger
except ImportError:
    class _Logger:
        def info(self, *a): print("[IMGPROVIDER]", *a)
        def error(self, *a): print("[IMGPROVIDER ERROR]", *a)
        def debug(self, *a): pass
    logger = _Logger()

from zentra.core.media.image_providers.utils import log_debug
from zentra.core.media.image_providers.pollinations import PollinationsProvider
from zentra.core.media.image_providers.gemini import GeminiProvider, GeminiNativeProvider
from zentra.core.media.image_providers.openai import OpenAIProvider
from zentra.core.media.image_providers.stability import StabilityProvider
from zentra.core.media.image_providers.airforce import AirforceProvider
from zentra.core.media.image_providers.huggingface import HuggingFaceProvider


# ── Registry & Engine ─────────────────────────────────────────────────────────

PROVIDERS = {
    "pollinations":   PollinationsProvider,
    "gemini":         GeminiProvider,
    "gemini_native":  GeminiNativeProvider,
    "openai":         OpenAIProvider,
    "stability":      StabilityProvider,
    "airforce":       AirforceProvider,
    "huggingface":    HuggingFaceProvider,
}

def get_models_for_provider(provider_name: str) -> list:
    """Return the model list for a given provider. Fetches dynamically if possible."""
    cls = PROVIDERS.get(provider_name.lower())
    if cls:
        try:
            return cls.get_models()
        except Exception as e:
            logger.error(f"[ImageEngine] Model list error for {provider_name}: {e}")
    return []


def generate_image(prompt: str, provider: str, model: str, width: int, height: int, api_key: str) -> str:
    """
    Main entry point. Returns the filename of the saved image.
    Raises Exception if generation fails.
    """
    provider = provider.lower()
    cls = PROVIDERS.get(provider)

    log_debug(f"[ImageEngine] START provider={provider} model={model} prompt={prompt[:60]}")

    if cls:
        try:
            filename = cls.generate(prompt, width, height, model, api_key)
            log_debug(f"[ImageEngine] SUCCESS via {provider} → {filename}")
            return filename
        except Exception as e:
            log_debug(f"[ImageEngine] {provider} failed: {e}")
            logger.error(f"[ImageEngine] {provider} failed: {e}. No automatic fallback.")
            raise Exception(f"{provider.capitalize()} failed to generate image: {e}")

    raise Exception(f"Il provider '{provider}' non possiede un motore nativo per la generazione di immagini. Selezionare un provider compatibile (es. OpenAI, Gemini Native, Pollinations, Hugging Face).")
