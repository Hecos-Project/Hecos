"""
hecos/core/global_presets/__init__.py
Preset Manager - Advanced Configuration Module for Hecos
Manages Global Presets containing personality (Soul), inference, voice, model, and payload settings.
"""

from .schema import (
    SoulProfile, SoulMeta, SoulPersona, SoulInference, SoulVoice, SoulModel, SoulPayload,
    GlobalPresetProfile, GlobalPresetMeta, GlobalPresetPersona,
    GlobalPresetInference, GlobalPresetVoice, GlobalPresetModel, GlobalPresetPayload,
    InferencePreset,
)
from .manager import (
    list_souls, get_soul, save_soul, duplicate_soul, delete_soul, get_active_soul, get_active_soul_id,
    list_presets, get_preset, save_preset, duplicate_preset, delete_preset, get_active_preset, get_active_preset_id,
    activate_soul_for_session, activate_preset_for_session, resolve_coder_preset_id,
)
from .inference_presets import list_inference_presets, get_inference_preset, save_inference_preset, delete_inference_preset
from .merger import merge_soul_into_config
from .usage_stats import (
    get_all_preset_usage,
    get_preset_usage,
    record_preset_usage,
    delete_preset_usage,
    resolve_soul_created_at,
)

# Aliases for easier imports
__all__ = [
    'GlobalPresetProfile', 'GlobalPresetMeta', 'GlobalPresetPersona',
    'GlobalPresetInference', 'GlobalPresetVoice', 'GlobalPresetModel', 'GlobalPresetPayload',
    'SoulProfile', 'SoulMeta', 'SoulPersona', 'SoulInference', 'SoulVoice', 'SoulModel', 'SoulPayload',
    'InferencePreset',
    'list_presets', 'get_preset', 'save_preset', 'duplicate_preset', 'delete_preset', 'get_active_preset', 'get_active_preset_id',
    'list_souls', 'get_soul', 'save_soul', 'duplicate_soul', 'delete_soul', 'get_active_soul', 'get_active_soul_id',
    'list_inference_presets', 'get_inference_preset', 'save_inference_preset', 'delete_inference_preset',
    'merge_soul_into_config',
    'get_all_preset_usage', 'get_preset_usage', 'record_preset_usage', 'delete_preset_usage', 'resolve_soul_created_at',
]

# Create default on first load if it doesn't exist
try:
    if not get_soul("hecos_default"):
        default_soul = SoulProfile()
        default_soul.meta.id = "hecos_default"
        default_soul.meta.name = "Hecos Default"
        default_soul.meta.description = "The standard Hecos configuration."
        default_soul.persona.soul_file = "Hecos_System_Soul"
        default_soul.inference.preset_name = "balanced"
        save_soul(default_soul)
except Exception:
    pass
