"""
MODULE: Media Config Schema
DESCRIPTION: Pydantic v2 model for config/media.yaml
"""

from typing import Any
from pydantic import BaseModel, Field


class ImageGenConfig(BaseModel):
    # ── Core ──────────────────────────────────────────────────────────────────
    enabled: bool = True
    provider: str = "pollinations"
    model: str = "flux"
    nologo: bool = True
    api_key: str = ""
    api_key_comment: str = ""

    # ── Dimensions ────────────────────────────────────────────────────────────
    # aspect_ratio takes precedence; width/height are used only when ratio='custom'
    aspect_ratio: str = "1:1"
    width: int = 1024
    height: int = 1024

    # ── Sampling ─────────────────────────────────────────────────────────────
    seed: int = -1                    # -1 = random every generation
    last_seed: int = -1               # stores the actual concrete seed used in the last run
    sampler: str = "euler_a"          # euler_a | ddim | dpm++2m | pndm | lms
    scheduler: str = "euler"          # euler | dpm++ | pndm | ddim
    guidance_scale: float = 7.5       # CFG scale — same concept, two names
    num_inference_steps: int = 30

    # ── Negative Prompt ───────────────────────────────────────────────────────
    enable_negative_prompt: bool = True
    negative_prompt: str = "distorted, extra fingers, malformed limbs, missing limbs, ugly, blurry, low quality"

    # ── Prompt Enhancement ────────────────────────────────────────────────────
    auto_enrich: bool = True
    enrich_keywords: str = "masterpiece, 8k wallpaper, highly detailed, realistic, sharp focus, cinematic lighting"
    style: str = "none"
    optimize_for_flux: bool = True
    flux_refiner_instructions: str = (
        "Convert keywords into a descriptive natural language paragraph for Flux. "
        "Convert keywords into a descriptive natural language paragraph for Flux. "
        "Output ONLY the optimised prompt, no preamble."
    )
    
    # ── Debug / Chat Options ──────────────────────────────────────────────────
    show_metadata_in_chat: bool = False

    # ── Preset System ─────────────────────────────────────────────────────────
    presets: dict[str, Any] = Field(default_factory=dict)
    active_preset: str = ""
    
    # ── Custom Models ─────────────────────────────────────────────────────────
    custom_hf_models: list[str] = Field(default_factory=list)


class VideoGenConfig(BaseModel):
    enabled: bool = False


class MediaConfig(BaseModel):
    """Root schema for config/media.yaml"""
    image_gen: ImageGenConfig = ImageGenConfig()
    video_gen: VideoGenConfig = VideoGenConfig()
