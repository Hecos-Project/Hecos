"""
MODULE: Widgets Config Schema
DESCRIPTION: Pydantic v2 models for config/widgets.yaml
             Contains sidebar and control room widget layout/persistence.
"""

from __future__ import annotations
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


# ─── WIDGET PERSISTENCE ───────────────────────────────────────────────────────

class WidgetPersistence(BaseModel):
    visible: bool = True
    room_visible: bool = False
    room_span: int = 1
    room_height: Optional[int] = None
    room_order: Optional[int] = None
    theme: str = "default"
    bg_color: str = ""
    bg_image: str = ""


class WidgetsConfig(BaseModel):
    model_config = ConfigDict(extra='allow')
    sidebar_order: List[str] = Field(default_factory=list)
    per_widget: Dict[str, WidgetPersistence] = Field(default_factory=dict)
    sidebar_status_collapsed: bool = False
    sidebar_audio_collapsed: bool = False
    sidebar_widgets_enabled: bool = True
    room_layout: List[str] = Field(default_factory=list)


# ─── ROOT SCHEMA FOR widgets.yaml ─────────────────────────────────────────────

class WidgetsFileConfig(BaseModel):
    """Root schema for config/widgets.yaml"""
    model_config = ConfigDict(extra='ignore')
    widgets: WidgetsConfig = Field(default_factory=WidgetsConfig)
