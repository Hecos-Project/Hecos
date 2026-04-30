"""
Plugin: Image Generation — Generator
Core generation loop: reads config, resolves params, builds prompt,
handles key rotation, retry logic, and delegates to the provider engine.
"""

import os

try:
    from hecos.core.logging import logger
    from hecos.core.media_config import get_media_config
    from hecos.core.media.image_providers import generate_image as _engine_generate
    from hecos.core.i18n import translator
except ImportError as _e:
    class _L:
        def info(self, *a): print("[GENERATOR]", *a)
        def warning(self, *a): print("[GENERATOR WARN]", *a)
        def error(self, *a): print("[GENERATOR ERR]", *a)
    logger = _L()
    def get_media_config(): return {"image_gen": {}}
    def _engine_generate(**kw): raise Exception("Core engine not available")
    class translator:
        @staticmethod
        def t(k, **kw): return k

from .dimensions import resolve_dimensions
from .prompt_engine import build_prompt


# ── Helpers ───────────────────────────────────────────────────────────────────

_RETRIABLE_SIGNALS = [
    "HTTP 402", "HTTP 429", "HTTP 503", "HTTP 500", "HTTP 504",
    "CUDA out of memory", "Model is loading",
    "Rate limit reached", "You have reached your limit",
    "server is overloaded", "upstream request timeout",
    "timed out", "timeout",
]


def _is_retriable(err_msg: str) -> bool:
    return any(sig.lower() in err_msg.lower() for sig in _RETRIABLE_SIGNALS)


def _get_api_key(provider: str, pinned_key: str) -> str:
    """Tries pinned key → KeyManager → OS env."""
    if pinned_key:
        return pinned_key

    try:
        from hecos.core.keys.key_manager import get_key_manager
        manager = get_key_manager()
        key = manager.get_key(provider)
        if key:
            logger.info(f"[GENERATOR] KeyManager returned key for {provider}")
            return key
    except ImportError:
        logger.error("[GENERATOR] Could not import KeyManager")

    # OS env fallback
    env_map = {
        "gemini":       "GEMINI_API_KEY",
        "gemini_native":"GEMINI_API_KEY",
        "openai":       "OPENAI_API_KEY",
        "stability":    "STABILITY_API_KEY",
        "huggingface":  "HUGGINGFACE_API_KEY",
    }
    var = env_map.get(provider, "")
    key = os.environ.get(var, "").strip()
    if key:
        logger.info(f"[GENERATOR] OS env fallback succeeded for {var}")
    return key


def _mark_exhausted(provider: str, api_key: str, err_msg: str) -> None:
    try:
        from hecos.core.keys.key_manager import get_key_manager
        manager = get_key_manager()
        reason = "rate_limited" if ("402" in err_msg or "429" in err_msg) else "server_overload"
        cooldown = 3600 if reason == "server_overload" else 60.0
        manager.mark_exhausted(provider, api_key, reason=reason, cooldown=cooldown)
    except Exception:
        pass


# ── Main Entry Point ──────────────────────────────────────────────────────────

def run_generation(raw_prompt: str) -> str:
    """
    Full generation pipeline.
    Returns the formatted response string (with [[IMG:filename]] tag) on success,
    or a human-readable error string on failure.
    """
    try:
        cfg = get_media_config().get("image_gen", {})

        # ── Config extraction ──────────────────────────────────────────────────
        provider    = cfg.get("provider", "pollinations")
        model       = cfg.get("model", "flux")
        aspect_ratio = cfg.get("aspect_ratio", "1:1")
        width       = int(cfg.get("width",  1024))
        height      = int(cfg.get("height", 1024))
        seed        = int(cfg.get("seed", -1))
        if seed < 0:
            import random
            seed = random.randint(1, 2147483647)
        
        # Persist the concrete seed used so the UI can offer 'Reuse Last Seed'
        try:
            from hecos.core.media_config import save_media_config
            full_media_cfg = get_media_config()
            if "image_gen" in full_media_cfg:
                full_media_cfg["image_gen"]["last_seed"] = seed
                save_media_config(full_media_cfg)
        except Exception as _e:
            logger.debug(f"[GENERATOR] Failed to persist last_seed: {_e}")
        sampler     = cfg.get("sampler", "euler_a")
        scheduler   = cfg.get("scheduler", "euler")
        pinned_key  = cfg.get("api_key", "").strip()

        neg_enabled = cfg.get("enable_negative_prompt", True)
        neg_prompt  = cfg.get("negative_prompt", "") if neg_enabled else ""
        guidance    = float(cfg.get("guidance_scale", 7.5))
        steps       = int(cfg.get("num_inference_steps", 30))

        optimize_flux       = cfg.get("optimize_for_flux", True)
        flux_instructions   = cfg.get("flux_refiner_instructions",
            "Convert keywords into a descriptive natural language paragraph for Flux. Output ONLY the optimised prompt, no preamble.")
        auto_enrich         = cfg.get("auto_enrich", True)
        enrich_keywords     = cfg.get("enrich_keywords", "")
        style               = cfg.get("style", "none")
        show_meta_chat      = cfg.get("show_metadata_in_chat", False)

        meta_str = ""
        if show_meta_chat:
            meta_str = f"\n\n> **[Image Gen Config]** Provider: `{provider}`, Model: `{model}`, Seed: `{seed}`, CFG: `{guidance}`, Sampler: `{sampler}`, Steps: `{steps}`"

        # ── Resolve dimensions from aspect ratio ──────────────────────────────
        final_width, final_height = resolve_dimensions(aspect_ratio, width, height)
        logger.info(f"[GENERATOR] Aspect ratio '{aspect_ratio}' → {final_width}×{final_height}")

        # ── Build prompt ──────────────────────────────────────────────────────
        final_prompt = build_prompt(
            raw_prompt=raw_prompt,
            style=style,
            auto_enrich=auto_enrich,
            enrich_keywords=enrich_keywords,
            model=model,
            optimize_for_flux=optimize_flux,
            flux_instructions=flux_instructions,
        )

        # ── Retry loop with key rotation ──────────────────────────────────────
        max_attempts = 5
        last_error   = None
        current_pinned = pinned_key  # may be cleared on failure

        for attempt in range(1, max_attempts + 1):
            api_key = _get_api_key(provider, current_pinned)

            if not api_key and provider not in ("pollinations", "airforce"):
                msg = (f"No API key available for '{provider}'. "
                       "Add at least one valid key in Key Manager or .env.")
                if last_error:
                    raise last_error
                raise Exception(msg)

            try:
                logger.info(f"[GENERATOR] Attempt {attempt}/{max_attempts} — {provider}/{model}")
                filename = _engine_generate(
                    prompt=final_prompt,
                    provider=provider,
                    model=model,
                    width=final_width,
                    height=final_height,
                    api_key=api_key,
                    negative_prompt=neg_prompt,
                    guidance_scale=guidance,
                    num_inference_steps=steps,
                    seed=seed,
                    sampler=sampler,
                    scheduler=scheduler,
                    # Pass through the remaining legacy params so the engine
                    # still handles enrichment for providers that need it
                    auto_enrich=False,  # already handled above
                    enrich_keywords="",
                    style="none",
                )

                # Format response
                clean_prompt = final_prompt.strip()
                if len(clean_prompt) > 250:
                    clean_prompt = clean_prompt[:247] + "..."
                prefix = translator.t("igen_response_prefix", prompt=clean_prompt)
                return f"{prefix}\n\n[[IMG:{filename}]]{meta_str}"

            except Exception as e:
                last_error = e
                err_msg = str(e)
                if _is_retriable(err_msg):
                    logger.warning(f"[GENERATOR] Retriable error on attempt {attempt}: {err_msg}")
                    _mark_exhausted(provider, api_key, err_msg)
                    current_pinned = ""  # clear pinned so next iteration tries KeyManager
                    continue
                raise  # non-retriable, propagate immediately

        raise last_error or Exception("Max generation attempts reached without success.")

    except Exception as e:
        logger.error(f"[GENERATOR] Generation failed: {e}")
        err_str = str(e)
        # Wrap with artist attribution if not already present
        if "Artist" not in err_str:
            provider_name = cfg.get("provider", "unknown").capitalize() if "cfg" in dir() else "Unknown"
            err_str = f"Artist [{provider_name}] rejected: {err_str}"
        return f"⚠️ Image generation failed. {err_str}. Verify provider config or prompt safety.{meta_str}"
