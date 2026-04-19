"""
MODULE: Media Config Schema
DESCRIPTION: Pydantic v2 model for config/media.yaml
"""

from pydantic import BaseModel


class ImageGenConfig(BaseModel):
    enabled: bool = True
    provider: str = "pollinations"
    model: str = "flux"
    width: int = 1024
    height: int = 1024
    nologo: bool = True
    api_key: str = ""
    api_key_comment: str = ""
    enable_negative_prompt: bool = True
    negative_prompt: str = "distorted, extra fingers, malformed limbs, missing limbs, ugly, blurry, low quality"
    guidance_scale: float = 7.5
    num_inference_steps: int = 30
    auto_enrich: bool = True
    enrich_keywords: str = "masterpiece, 8k wallpaper, highly detailed, realistic, sharp focus, cinematic lighting"
    style: str = "none"
    optimize_for_flux: bool = True
    flux_refiner_instructions: str = "Convert keywords into a descriptive natural language paragraph for Flux. Output ONLY the optimized prompt, no preamble."


class VideoGenConfig(BaseModel):
    enabled: bool = False


class MediaConfig(BaseModel):
    """Root schema for config/media.yaml"""
    image_gen: ImageGenConfig = ImageGenConfig()
    video_gen: VideoGenConfig = VideoGenConfig()
