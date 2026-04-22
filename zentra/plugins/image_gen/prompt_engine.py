"""
Plugin: Image Generation — Prompt Engine
Handles all prompt transformations:
  - Style modifier injection
  - Auto-enrichment keywords
  - Flux LLM-based refinement
"""

try:
    from zentra.core.logging import logger
except ImportError:
    class _L:
        def info(self, *a): print("[PROMPT_ENGINE]", *a)
        def warning(self, *a): print("[PROMPT_ENGINE WARN]", *a)
        def error(self, *a): print("[PROMPT_ENGINE ERR]", *a)
    logger = _L()


# ── Style Map ─────────────────────────────────────────────────────────────────

STYLE_MAP: dict[str, str] = {
    "cinematic":   "cinematic photo, highly detailed, dramatic lighting, 8k",
    "photography": "professional photography, DSLR, ultra-realistic, 8k, sharp focus",
    "anime":       "anime style, vibrant colors, expressive features, clean lines",
    "manga":       "manga style, black and white, detailed ink drawing, hatch lines",
    "cartoon":     "cartoon style, playful, simplified shapes, bright colors, 2d",
    "digital_art": "digital art, concept art, artistic, detailed illustration",
    "oil_painting":"oil painting, textured brushstrokes, classical art style, canvas",
    "sketch":      "pencil sketch, hand-drawn, graphite, artist study, white background",
    "3d_render":   "3D rendering, Octane Render, Unreal Engine 5, highly detailed, photorealistic",
    "cyberpunk":   "cyberpunk style, neon lights, rainy streets, futuristic, high tech",
    "fantasy":     "fantasy art, magical, ethereal, epic scale, mythical",
    "watercolor":  "watercolor painting, soft washes, fluid strokes, pale tones",
    "pixel_art":   "pixel art, retro style, 16-bit, crisp pixels, limited palette",
}


def apply_style(prompt: str, style: str) -> str:
    """Appends a style modifier to the prompt if a valid style is selected."""
    if not style or style.lower() == "none":
        return prompt
    modifier = STYLE_MAP.get(style.lower())
    if modifier:
        return f"{prompt}, {modifier}"
    return prompt


def apply_enrichment(prompt: str, auto_enrich: bool, enrich_keywords: str) -> str:
    """Appends quality enrichment keywords if enabled and not already present."""
    if not auto_enrich:
        return prompt
    terms = enrich_keywords.strip() if enrich_keywords else \
        "masterpiece, 8k wallpaper, highly detailed, realistic, sharp focus, cinematic lighting"
    # Avoid duplicating keywords that are already in the prompt
    if "masterpiece" not in prompt.lower() and "8k" not in prompt.lower():
        return f"{prompt}, {terms}"
    return prompt


def refine_flux_prompt(original_prompt: str, instructions: str) -> str:
    """
    Uses Zentra's LLM brain to rewrite a keyword-style prompt into
    a natural language paragraph optimised for Flux.
    Falls back to the original prompt on any error.
    """
    try:
        from zentra.core.llm import client
        from zentra.core.media_config import get_media_config
        from zentra.app.config import ConfigManager
        from app.model_manager import ModelManager

        main_cfg = ConfigManager().config

        system_prompt = (
            "You are an expert prompt engineer specialising in the Flux image generation model. "
            "Flux prefers detailed, natural language descriptions over comma-separated tags. "
            f"{instructions}"
        )
        user_msg = f"Optimise this prompt for Flux: {original_prompt}"

        effective_backend_type, effective_default_model = ModelManager.get_effective_model_info(main_cfg)
        backend_config = main_cfg.get("backend", {}).get(effective_backend_type, {}).copy()
        backend_config["model"] = effective_default_model
        backend_config["backend_type"] = effective_backend_type
        llm_cfg = main_cfg.get("llm", {})

        logger.info(f"[PROMPT_ENGINE] Refining prompt for Flux via {effective_backend_type}...")

        refined = client.generate(system_prompt, user_msg, backend_config, llm_cfg)

        if refined and not isinstance(refined, dict) and not refined.startswith("⚠️"):
            cleaned = refined.strip().strip('"').strip("'")
            logger.info(f"[PROMPT_ENGINE] Flux prompt refined: {cleaned[:60]}...")
            return cleaned

        logger.warning("[PROMPT_ENGINE] LLM returned empty/error — using original prompt.")
        return original_prompt

    except Exception as e:
        logger.error(f"[PROMPT_ENGINE] Flux refinement failed: {e}")
        return original_prompt


def build_prompt(
    raw_prompt: str,
    style: str,
    auto_enrich: bool,
    enrich_keywords: str,
    model: str,
    optimize_for_flux: bool,
    flux_instructions: str,
) -> str:
    """
    Full prompt pipeline:
      1. Flux LLM refinement (if model is Flux and enabled)
      2. Style modifier injection
      3. Auto-enrichment keywords
    """
    # Flux: LLM refine first, then skip tag-based enrichment
    if optimize_for_flux and "flux" in model.lower():
        logger.info("[PROMPT_ENGINE] Flux optimisation enabled — calling Brain refiner.")
        prompt = refine_flux_prompt(raw_prompt, flux_instructions)
        # Style still applies even for Flux
        return apply_style(prompt, style)

    # Non-Flux: style → enrichment
    prompt = apply_style(raw_prompt, style)
    prompt = apply_enrichment(prompt, auto_enrich, enrich_keywords)
    return prompt
