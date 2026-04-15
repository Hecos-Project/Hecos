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
    negative_prompt: str = "distorted, extra fingers, malformed limbs, missing limbs, ugly, blurry, low quality"
    guidance_scale: float = 7.5
    num_inference_steps: int = 30
    auto_enrich: bool = True


class VideoGenConfig(BaseModel):
    enabled: bool = False


class MediaConfig(BaseModel):
    """Root schema for config/media.yaml"""
    image_gen: ImageGenConfig = ImageGenConfig()
    video_gen: VideoGenConfig = VideoGenConfig()
