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


def generate_image(prompt: str, provider: str, model: str, width: int, height: int, api_key: str, 
                   negative_prompt: str = "", guidance_scale: float = 7.5, 
                   num_inference_steps: int = 30, auto_enrich: bool = False,
                   enrich_keywords: str = "", style: str = "none") -> str:
    """
    Main entry point. Returns the filename of the saved image.
    Raises Exception if generation fails.
    """
    provider = provider.lower()
    cls = PROVIDERS.get(provider)

    # 0. Style & Prompt Enrichment
    final_prompt = prompt
    
    # Apply Style Modifier
    if style and style.lower() != "none":
        style_map = {
            "cinematic": "cinematic photo, highly detailed, dramatic lighting, 8k",
            "photography": "professional photography, DSLR, ultra-realistic, 8k, sharp focus",
            "anime": "anime style, vibrant colors, expressive features, clean lines",
            "manga": "manga style, black and white, detailed ink drawing, hatch lines",
            "cartoon": "cartoon style, playful, simplified shapes, bright colors, 2d",
            "digital_art": "digital art, concept art, artistic, detailed illustration",
            "oil_painting": "oil painting, textured brushstrokes, classical art style, canvas",
            "sketch": "pencil sketch, hand-drawn, graphite, artist study, white background",
            "3d_render": "3D rendering, Octane Render, Unreal Engine 5, highly detailed, photorealistic",
            "cyberpunk": "cyberpunk style, neon lights, rainy streets, futuristic, high tech",
            "fantasy": "fantasy art, magical, ethereal, epic scale, mythical"
        }
        modifier = style_map.get(style.lower())
        if modifier:
            final_prompt = f"{final_prompt}, {modifier}"

    # Apply Auto-Enrichment
    if auto_enrich:
        terms = enrich_keywords if enrich_keywords else "masterpiece, 8k wallpaper, highly detailed, realistic, sharp focus, cinematic lighting"
        # Only add if the core terms aren't already there (simple check)
        if "masterpiece" not in prompt.lower() and "8k" not in prompt.lower():
            final_prompt = f"{final_prompt}, {terms}"

    log_debug(f"[ImageEngine] START provider={provider} model={model} prompt={final_prompt[:60]}")

    if cls:
        try:
            # We use a kwargs approach to be flexible with provider signatures
            # but for now we update all known providers.
            filename = cls.generate(
                prompt=final_prompt, 
                width=width, 
                height=height, 
                model=model, 
                api_key=api_key,
                negative_prompt=negative_prompt,
                guidance_scale=guidance_scale,
                num_inference_steps=num_inference_steps
            )
            log_debug(f"[ImageEngine] SUCCESS via {provider} → {filename}")
            return filename
        except Exception as e:
            err_msg = str(e)
            # Standardize common safety-related HTTP errors if possible, unless it's a known hardware/loading issue
            if "400" in err_msg and "CUDA out of memory" not in err_msg and "loading" not in err_msg:
                err_msg = f"Potential safety/content block ({err_msg})"
            
            log_debug(f"[ImageEngine] {provider} failed: {err_msg}")
            logger.error(f"[ImageEngine] {provider} failed: {err_msg}. No automatic fallback.")
            raise Exception(f"Artist [{provider.capitalize()}] rejected: {err_msg}")

    raise Exception(f"Il provider '{provider}' non possiede un motore nativo per la generazione di immagini. Selezionare un provider compatibile (es. OpenAI, Gemini Native, Pollinations, Hugging Face).")
