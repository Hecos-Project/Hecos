"""
Plugin: Image Generation â€” Preset Manager
Manages built-in (read-only) and user-defined (CRUD) configuration presets.
Reads/writes from the package's own config manager.
"""

from __future__ import annotations
from typing import Any

try:
    from hecos.core.logging import logger
except ImportError:
    class _L:
        def info(self, *a): print("[PRESETS]", *a)
        def error(self, *a): print("[PRESETS ERR]", *a)
    logger = _L()


BUILTIN_PRESETS: dict[str, dict[str, Any]] = {
    "⚡ Flux Free (Pollinations)": {
        "provider": "pollinations",
        "model": "flux",
        "aspect_ratio": "1:1",
        "guidance_scale": 0.0,
        "num_inference_steps": 4,
        "seed": -1,
        "sampler": "euler",
        "scheduler": "simple",
        "negative_prompt": "",
        "enable_negative_prompt": False,
        "auto_enrich": False,
        "optimize_for_flux": True,
        "style": "none",
        "_builtin": True,
        "_description": "Free, no API key required. Uses Pollinations with Flux model.",
    },
    "🖼️ SDXL (HuggingFace)": {
        "provider": "huggingface",
        "model": "stabilityai/stable-diffusion-xl-base-1.0",
        "aspect_ratio": "1:1",
        "guidance_scale": 7.5,
        "num_inference_steps": 40,
        "seed": -1,
        "sampler": "dpm++2m",
        "scheduler": "dpm++",
        "negative_prompt": "distorted, extra fingers, malformed limbs, missing limbs, ugly, blurry, low quality",
        "enable_negative_prompt": True,
        "auto_enrich": True,
        "optimize_for_flux": False,
        "style": "none",
        "_builtin": True,
        "_description": "Stable Diffusion XL via HuggingFace Inference API. Requires HF API key.",
    },
    "🎨 SD 1.5 1B (HuggingFace)": {
        "provider": "huggingface",
        "model": "runwayml/stable-diffusion-v1-5",
        "aspect_ratio": "1:1",
        "guidance_scale": 7.5,
        "num_inference_steps": 30,
        "seed": -1,
        "sampler": "euler_a",
        "scheduler": "pndm",
        "negative_prompt": "distorted, extra fingers, malformed limbs, ugly, blurry, low quality",
        "enable_negative_prompt": True,
        "auto_enrich": True,
        "optimize_for_flux": False,
        "style": "none",
        "_builtin": True,
        "_description": "Stable Diffusion 1.5 (~1B params). Fast, lighter on HF quota.",
    },
    "⚡ Flux Schnell (HuggingFace)": {
        "provider": "huggingface",
        "model": "black-forest-labs/FLUX.1-schnell",
        "aspect_ratio": "1:1",
        "guidance_scale": 0.0,
        "num_inference_steps": 4,
        "seed": -1,
        "sampler": "euler",
        "scheduler": "simple",
        "negative_prompt": "",
        "enable_negative_prompt": False,
        "auto_enrich": False,
        "optimize_for_flux": True,
        "style": "none",
        "_builtin": True,
        "_description": "Flux Schnell via HuggingFace. Very fast (4 steps). Requires HF API key.",
    },
}


def get_all_presets(user_presets: dict) -> dict[str, dict]:
    combined = dict(BUILTIN_PRESETS)
    combined.update(user_presets)
    return combined


def get_preset(name: str, user_presets: dict) -> dict | None:
    return get_all_presets(user_presets).get(name)


def save_user_preset(name: str, config_snapshot: dict) -> bool:
    import sys, os
    try:
        from igen_config.config_manager import get_config, save_config
    except ImportError:
        # Fallback if imported inside Hecos plugin loader
        from ..igen_config.config_manager import get_config, save_config

    if not name or not name.strip():
        logger.error("[PRESETS] Cannot save preset with empty name.")
        return False
    name = name.strip()
    if name in BUILTIN_PRESETS:
        logger.error(f"[PRESETS] '{name}' is a built-in preset and cannot be overwritten.")
        return False

    try:
        cfg = get_config()
        igen = cfg.get("image_gen", {})
        presets = igen.get("presets", {})
        
        snapshot = {k: v for k, v in config_snapshot.items()
                    if not k.startswith("_") and k != "presets" and k != "active_preset"}
        presets[name] = snapshot
        
        igen["presets"] = presets
        cfg["image_gen"] = igen
        ok = save_config(cfg)
        if ok:
            logger.info(f"[PRESETS] Saved user preset '{name}'.")
        return ok
    except Exception as e:
        logger.error(f"[PRESETS] Failed saving preset '{name}': {e}")
        return False


def delete_user_preset(name: str) -> bool:
    import sys, os
    try:
        from igen_config.config_manager import get_config, save_config
    except ImportError:
        # Fallback if imported inside Hecos plugin loader
        from ..igen_config.config_manager import get_config, save_config

    if name in BUILTIN_PRESETS:
        logger.error(f"[PRESETS] '{name}' is a built-in preset and cannot be deleted.")
        return False

    try:
        cfg = get_config()
        igen = cfg.get("image_gen", {})
        presets = igen.get("presets", {})
        if name not in presets:
            logger.error(f"[PRESETS] Preset '{name}' not found.")
            return False
            
        del presets[name]
        igen["presets"] = presets
        cfg["image_gen"] = igen
        ok = save_config(cfg)
        if ok:
            logger.info(f"[PRESETS] Deleted user preset '{name}'.")
        return ok
    except Exception as e:
        logger.error(f"[PRESETS] Failed deleting preset '{name}': {e}")
        return False

