from typing import List
from pydantic import BaseModel, ConfigDict, Field

class PresenterVoiceConfig(BaseModel):
    enabled: bool = False
    preset_id: str = "" # Uses global presets to set up cloud capabilities
    events: List[str] = Field(default_factory=lambda: ["persona_switched", "new_chat"])
    persona_self_intro: bool = True
    max_tokens: int = 60
    timeout_s: int = 8
    rate_per_min: int = 3

class PresenterFeedConfig(BaseModel):
    persist: bool = True
    max_items: int = 50
    max_file_mb: int = 5
    backups: int = 3

class PresenterConfig(BaseModel):
    model_config = ConfigDict(extra='ignore')

    enabled: bool = True
    panel_default: str = "collapsed"
    briefing_on_new_chat: bool = True
    briefing_sections: List[str] = Field(default_factory=lambda: ["system", "backend", "persona", "tips"])
    toast_seconds: int = 5
    
    live_commentary: bool = True
    commentary_on_messages: bool = False
    verbosity: str = "normal"
    log_level: str = "warning"

    voice: PresenterVoiceConfig = Field(default_factory=PresenterVoiceConfig)
    feed: PresenterFeedConfig = Field(default_factory=PresenterFeedConfig)
