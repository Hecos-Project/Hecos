"""
image_gen package — Config Manager (Pydantic + TOML)
Reads/writes the package's own image_gen.toml using Hecos HPMBaseConfigManager.
"""
import os
from pathlib import Path
from typing import Any, Dict
from pydantic import BaseModel, Field

try:
    from hecos.core.logging import logger
    from hecos.core.package_manager.config import HPMBaseConfigManager
except ImportError:
    # Fallback for isolated testing
    class _L:
        def info(self, *a): print("[IMAGE_GEN CONFIG]", *a)
        def error(self, *a): print("[IMAGE_GEN CONFIG ERR]", *a)
        def warning(self, *a): print("[IMAGE_GEN CONFIG WARN]", *a)
    logger = _L()
    class HPMBaseConfigManager:
        pass


class ImageGenConfig(BaseModel):
    # ── Core ──────────────────────────────────────────────────────────────────
    enabled: bool = True
    provider: str = "pollinations"
    model: str = "flux"
    nologo: bool = True
    api_key: str = ""
    api_key_comment: str = ""

    # ── Dimensions ────────────────────────────────────────────────────────────
    aspect_ratio: str = "1:1"
    width: int = 1024
    height: int = 1024

    # ── Sampling ─────────────────────────────────────────────────────────────
    seed: int = -1                    
    last_seed: int = -1               
    sampler: str = "euler"            
    scheduler: str = "simple"         
    guidance_scale: float = 0.0       
    num_inference_steps: int = 4      

    # ── Negative Prompt ───────────────────────────────────────────────────────
    enable_negative_prompt: bool = False
    negative_prompt: str = ""

    # ── Prompt Enhancement ────────────────────────────────────────────────────
    auto_enrich: bool = False
    enrich_keywords: str = ""
    style: str = "none"
    optimize_for_flux: bool = True
    flux_refiner_instructions: str = (
        "Convert keywords into a descriptive natural language paragraph for Flux. "
        "Output ONLY the optimised prompt, no preamble."
    )
    
    # ── Debug / Chat Options ──────────────────────────────────────────────────
    show_metadata_in_chat: bool = False

    # ── Preset System ─────────────────────────────────────────────────────────
    presets: Dict[str, Any] = Field(default_factory=dict)
    active_preset: str = ""
    
    # ── Custom Models ─────────────────────────────────────────────────────────
    custom_hf_models: list[str] = Field(default_factory=list)


_THIS_DIR = Path(__file__).parent.resolve()
_CONFIG_FILE = _THIS_DIR / "image_gen.toml"

_manager = None
if hasattr(HPMBaseConfigManager, "get"):
    _manager = HPMBaseConfigManager(ImageGenConfig, _CONFIG_FILE, "image_gen")


def get_config() -> dict:
    """Returns the full image_gen config dict for backwards compatibility."""
    if _manager:
        # We need to recreate the migration logic if needed? 
        # Actually HPMBaseConfigManager handles creating from defaults automatically!
        # If we need the legacy yaml migration, we can hook it here.
        obj = _manager.get()
        return {"image_gen": obj.model_dump(mode='json')}
    return {"image_gen": ImageGenConfig().model_dump(mode='json')}


def get_image_gen_config() -> dict:
    """Returns just the [image_gen] section."""
    return get_config().get("image_gen", {})


def save_config(data: dict) -> bool:
    """Saves the full config dict to image_gen.toml."""
    if _manager and "image_gen" in data:
        try:
            obj = ImageGenConfig.model_validate(data["image_gen"])
            return _manager.save(obj)
        except Exception as e:
            logger.error(f"[IMAGE_GEN] Validation error on save: {e}")
            return False
    return False


def save_image_gen_section(section: dict) -> bool:
    """Saves just the [image_gen] section, merging with existing config."""
    if not _manager: return False
    current = _manager.get().model_dump(mode='json')
    current.update(section)
    try:
        obj = ImageGenConfig.model_validate(current)
        return _manager.save(obj)
    except Exception as e:
        logger.error(f"[IMAGE_GEN] Validation error on merge: {e}")
        return False

