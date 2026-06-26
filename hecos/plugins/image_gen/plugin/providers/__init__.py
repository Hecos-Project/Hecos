"""
image_gen providers registry — autonomous engine.
Migrated from hecos/core/media/image_providers/__init__.py
"""

try:
    from hecos.core.logging import logger
except ImportError:
    class _Logger:
        def info(self, *a): print("[IMGPROVIDER]", *a)
        def error(self, *a): print("[IMGPROVIDER ERROR]", *a)
        def debug(self, *a): pass
    logger = _Logger()

from .utils import log_debug
from .pollinations import PollinationsProvider
from .gemini import GeminiProvider, GeminiNativeProvider
from .openai import OpenAIProvider
from .stability import StabilityProvider
from .airforce import AirforceProvider
from .huggingface import HuggingFaceProvider

PROVIDERS = {
    "pollinations":  PollinationsProvider,
    "gemini":        GeminiProvider,
    "gemini_native": GeminiNativeProvider,
    "openai":        OpenAIProvider,
    "stability":     StabilityProvider,
    "airforce":      AirforceProvider,
    "huggingface":   HuggingFaceProvider,
}


def get_models_for_provider(provider_name: str) -> list:
    cls = PROVIDERS.get(provider_name.lower())
    if cls:
        try:
            return cls.get_models()
        except Exception as e:
            logger.error(f"[ImageEngine] Model list error for {provider_name}: {e}")
    return []


def generate_image(prompt: str, provider: str, model: str, width: int, height: int,
                   api_key: str, negative_prompt: str = "", guidance_scale: float = 7.5,
                   num_inference_steps: int = 30, auto_enrich: bool = False,
                   enrich_keywords: str = "", style: str = "none",
                   seed: int = -1, sampler: str = "", scheduler: str = "") -> str:
    """
    Main entry point. Returns the filename of the saved image, raises Exception on failure.
    Note: prompt enrichment should be applied BEFORE calling this (via prompt_engine.py).
    auto_enrich/style are kept for backwards compatibility.
    """
    provider = provider.lower()
    cls = PROVIDERS.get(provider)

    if cls:
        try:
            filename = cls.generate(
                prompt=prompt, width=width, height=height, model=model, api_key=api_key,
                negative_prompt=negative_prompt, guidance_scale=guidance_scale,
                num_inference_steps=num_inference_steps, seed=seed,
                sampler=sampler, scheduler=scheduler,
            )
            log_debug(f"[ImageEngine] SUCCESS via {provider} → {filename}")
            return filename
        except Exception as e:
            err_msg = str(e)
            if "400" in err_msg and "CUDA out of memory" not in err_msg and "loading" not in err_msg:
                err_msg = f"Potential safety/content block ({err_msg})"
            log_debug(f"[ImageEngine] {provider} failed: {err_msg}")
            logger.error(f"[ImageEngine] {provider} failed: {err_msg}")
            raise Exception(f"Artist [{provider.capitalize()}] rejected: {err_msg}")

    raise Exception(
        f"Provider '{provider}' has no native image generation engine. "
        "Select a compatible provider (e.g. OpenAI, Gemini Native, Pollinations, Hugging Face)."
    )
