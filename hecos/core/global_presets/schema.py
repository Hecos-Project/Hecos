"""
hecos/core/global_presets/schema.py
Pydantic v2 models for the Global Preset (Soul) and Inference Presets.
"""

from typing import Optional, List, Dict
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime

# ── Inference Presets ──

class InferencePreset(BaseModel):
    model_config = ConfigDict(extra='ignore')
    
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    repeat_penalty: Optional[float] = None
    num_predict: Optional[int] = None
    num_ctx: Optional[int] = None
    max_tokens: Optional[int] = None
    description: str = ""

class InferencePresetsFile(BaseModel):
    presets: Dict[str, InferencePreset] = Field(default_factory=dict)

# ── Soul Profile (Global Preset) ──

class SoulMeta(BaseModel):
    id: str = "default_soul"
    name: str = "Default Soul"
    description: str = ""
    author: str = "Hecos"
    version: str = "1.0.0"
    tags: List[str] = Field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    icon: str = "🧠"

class SoulPersona(BaseModel):
    soul_file: Optional[str] = None
    special_instructions: Optional[str] = None # Legacy/override
    safety_instructions: Optional[str] = None # Legacy/override
    use_global_direct_instructions: Optional[bool] = None
    use_global_safety_instructions: Optional[bool] = None
    custom_instructions: Optional[str] = None

class SoulInference(BaseModel):
    preset_name: Optional[str] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    repeat_penalty: Optional[float] = None
    num_predict: Optional[int] = None
    num_ctx: Optional[int] = None
    max_tokens: Optional[int] = None
    n_gpu_layers: Optional[int] = None

class SoulVoice(BaseModel):
    tts_engine: Optional[str] = None
    tts_voice: Optional[str] = None
    xtts_preset: Optional[str] = None
    xtts_inference_preset: Optional[str] = None
    xtts_temperature: Optional[float] = None
    xtts_repetition_penalty: Optional[float] = None
    xtts_top_k: Optional[int] = None
    xtts_top_p: Optional[float] = None
    xtts_speed: Optional[float] = None
    xtts_length_penalty: Optional[float] = None
    xtts_speaker_wav: Optional[str] = None
    piper_speed: Optional[float] = None
    piper_noise_scale: Optional[float] = None
    piper_noise_w: Optional[float] = None
    kokoro_speed: Optional[float] = None
    kokoro_voice: Optional[str] = None

class SoulModel(BaseModel):
    backend_type: Optional[str] = None
    model_name: Optional[str] = None

class SoulProfile(BaseModel):
    model_config = ConfigDict(extra='ignore')
    
    meta: SoulMeta = Field(default_factory=SoulMeta)
    persona: SoulPersona = Field(default_factory=SoulPersona)
    inference: SoulInference = Field(default_factory=SoulInference)
    voice: SoulVoice = Field(default_factory=SoulVoice)
    model: SoulModel = Field(default_factory=SoulModel)
