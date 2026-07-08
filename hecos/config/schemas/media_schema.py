"""
MODULE: Media Config Schema
DESCRIPTION: Pydantic v2 model for config/media.yaml

NOTE: image_gen configuration is intentionally NOT here.
The image_gen package is a fully autonomous HPM package that manages
its own config via image_gen.toml inside the package directory.
Adding image_gen fields here would cause media.yaml to be polluted
with image_gen defaults every time the media config is saved.
"""

from pydantic import BaseModel


class VideoGenConfig(BaseModel):
    enabled: bool = False


class MediaConfig(BaseModel):
    """Root schema for config/media.yaml.
    Only contains media-related core settings. Package-specific
    configs (e.g. image_gen) are managed by their own packages.
    """
    video_gen: VideoGenConfig = VideoGenConfig()
