"""
MODULE: Vision (Multimodal Perception) Config Schema
DESCRIPTION: Pydantic v2 model for config/vision.yaml
"""
from typing import Optional
from pydantic import BaseModel, Field


class VisionBridgeConfig(BaseModel):
    """Configuration for the Vision Bridge / Sidecar (gives vision to text-only models)."""
    enabled: bool = Field(default=True, description="Enable vision bridge for text-only models")
    mode: str = Field(default="auto", description="Bridge mode: local_ollama | cloud | active_model | auto | disabled")
    cloud_model: str = Field(default="gemini/gemini-2.5-flash", description="Cloud vision model for rapid image inspection")
    local_model: str = Field(default="default", description="Ollama vision model (or 'default' to use active chat model)")
    inspection_prompt: str = Field(
        default="Describe in detail and objectively the visual elements of the image: subjects, actions, visible text, colors, setting, and notable details.",
        description="Prompt sent to the vision inspector model"
    )


class VisionNetSearchConfig(BaseModel):
    """Configuration for Net Search multimodal visual verification."""
    verify_results: bool = Field(default=True, description="Whether the AI visually inspects search result thumbnails")
    max_thumbnails: int = Field(default=4, ge=1, le=12, description="Max thumbnails to review per search query")


class VisionConfig(BaseModel):
    """Root schema for config/vision.yaml"""
    enabled: bool = Field(default=True, description="Master switch for vision / multimodal perception")
    max_resolution_px: int = Field(default=512, ge=256, le=2048, description="Max width/height for image resizing")
    jpeg_quality: int = Field(default=80, ge=30, le=100, description="JPEG quality for encoded images")
    timeout_seconds: int = Field(default=5, ge=2, le=30, description="Download timeout for external images")
    bridge: VisionBridgeConfig = Field(default_factory=VisionBridgeConfig)
    net_search: VisionNetSearchConfig = Field(default_factory=VisionNetSearchConfig)
