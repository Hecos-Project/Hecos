"""
hecos/core/global_presets/__init__.py
Soul Forge - Advanced Configuration Module for Hecos
Manages Global Presets (Souls) containing personality, inference, voice, and model settings.
"""

from .schema import SoulProfile, SoulMeta, SoulPersona, SoulInference, SoulVoice, SoulModel
from .schema import InferencePreset
from .manager import list_souls, get_soul, save_soul, delete_soul, get_active_soul, get_active_soul_id
from .inference_presets import list_inference_presets, get_inference_preset, save_inference_preset, delete_inference_preset
from .merger import merge_soul_into_config

# Aliases for easier imports
__all__ = [
    'SoulProfile', 'SoulMeta', 'SoulPersona', 'SoulInference', 'SoulVoice', 'SoulModel',
    'InferencePreset',
    'list_souls', 'get_soul', 'save_soul', 'delete_soul', 'get_active_soul', 'get_active_soul_id',
    'list_inference_presets', 'get_inference_preset', 'save_inference_preset', 'delete_inference_preset',
    'merge_soul_into_config'
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
