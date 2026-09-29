"""
hecos/core/global_presets/merger.py
Logic for merging a SoulProfile into a global config dictionary.
"""

from typing import Dict, Any
from hecos.core.logging import logger
from hecos.core.global_presets.schema import SoulProfile
from hecos.core.global_presets.inference_presets import get_inference_preset
import copy

def merge_soul_into_config(global_config: Dict[str, Any], soul: SoulProfile) -> Dict[str, Any]:
    """
    Returns a deep copy of global_config merged with the settings from the SoulProfile.
    Applies the override cascade:
    1. Global Config (base)
    2. Soul Persona
    3. Inference Preset (if specified)
    4. Inference Inline (overrides preset)
    5. Voice Preset / XTTS params
    6. Model backend settings
    """
    if not soul:
        return global_config
        
    logger.debug(f"[GlobalPresets] Merging Global Preset (Soul) '{soul.meta.name}' into config")
    merged = copy.deepcopy(global_config)
    
    # -- Persona Layer --
    if soul.persona.soul_file:
        if 'ai' not in merged: merged['ai'] = {}
        merged['ai']['active_personality'] = soul.persona.soul_file
        
    if soul.persona.special_instructions is not None:
        if 'ai' not in merged: merged['ai'] = {}
        merged['ai']['special_instructions'] = soul.persona.special_instructions
        
    if soul.persona.safety_instructions is not None:
        if 'ai' not in merged: merged['ai'] = {}
        merged['ai']['safety_instructions'] = soul.persona.safety_instructions

    # -- Model Layer --
    if soul.model.backend_type:
        if 'backend' not in merged: merged['backend'] = {}
        btype = soul.model.backend_type
        merged['backend']['type'] = btype
        if soul.model.model_name:
            if btype not in merged['backend']: merged['backend'][btype] = {}
            merged['backend'][btype]['model'] = soul.model.model_name

    # -- Inference Layer --
    # Find active backend dictionary to apply params to
    btype = merged.get('backend', {}).get('type', 'ollama')
    backend_dict = merged.get('backend', {}).get(btype, {})
    
    # 1. Apply Preset
    if soul.inference.preset_name:
        preset = get_inference_preset(soul.inference.preset_name)
        if preset:
            if preset.temperature is not None: backend_dict['temperature'] = preset.temperature
            if preset.top_p is not None: backend_dict['top_p'] = preset.top_p
            if preset.repeat_penalty is not None: backend_dict['repeat_penalty'] = preset.repeat_penalty
            if preset.num_predict is not None: backend_dict['num_predict'] = preset.num_predict
            if preset.num_ctx is not None: backend_dict['num_ctx'] = preset.num_ctx
            if preset.max_tokens is not None: backend_dict['max_tokens'] = preset.max_tokens
            
    # 2. Apply Inline Overrides (takes precedence)
    if soul.inference.temperature is not None: backend_dict['temperature'] = soul.inference.temperature
    if soul.inference.top_p is not None: backend_dict['top_p'] = soul.inference.top_p
    if soul.inference.repeat_penalty is not None: backend_dict['repeat_penalty'] = soul.inference.repeat_penalty
    if soul.inference.num_predict is not None: backend_dict['num_predict'] = soul.inference.num_predict
    if soul.inference.num_ctx is not None: backend_dict['num_ctx'] = soul.inference.num_ctx
    if soul.inference.max_tokens is not None: backend_dict['max_tokens'] = soul.inference.max_tokens
    if soul.inference.n_gpu_layers is not None: backend_dict['n_gpu_layers'] = soul.inference.n_gpu_layers

    # Write back
    if 'backend' not in merged: merged['backend'] = {}
    merged['backend'][btype] = backend_dict

    # -- Voice Layer --
    if 'ai' not in merged: merged['ai'] = {}
    
    if soul.voice.tts_engine:
        merged['ai']['tts_engine'] = soul.voice.tts_engine
        
    if soul.voice.tts_voice:
        merged['ai']['tts_voice'] = soul.voice.tts_voice
        
    # We pass these down to the XTTS engine via session_overrides if they exist
    voice_overrides = {}
    if soul.voice.xtts_preset: voice_overrides['xtts_preset'] = soul.voice.xtts_preset
    if soul.voice.xtts_temperature is not None: voice_overrides['xtts_temperature'] = soul.voice.xtts_temperature
    if soul.voice.xtts_repetition_penalty is not None: voice_overrides['xtts_repetition_penalty'] = soul.voice.xtts_repetition_penalty
    if soul.voice.xtts_top_k is not None: voice_overrides['xtts_top_k'] = soul.voice.xtts_top_k
    if soul.voice.xtts_top_p is not None: voice_overrides['xtts_top_p'] = soul.voice.xtts_top_p
    if soul.voice.xtts_speed is not None: voice_overrides['xtts_speed'] = soul.voice.xtts_speed
    if soul.voice.xtts_length_penalty is not None: voice_overrides['xtts_length_penalty'] = soul.voice.xtts_length_penalty
    if soul.voice.xtts_speaker_wav is not None: voice_overrides['xtts_speaker_wav'] = soul.voice.xtts_speaker_wav
    
    if soul.voice.piper_speed is not None: voice_overrides['piper_speed'] = soul.voice.piper_speed
    if soul.voice.piper_noise_scale is not None: voice_overrides['piper_noise_scale'] = soul.voice.piper_noise_scale
    if soul.voice.piper_noise_w is not None: voice_overrides['piper_noise_w'] = soul.voice.piper_noise_w
    
    if soul.voice.kokoro_speed is not None: voice_overrides['kokoro_speed'] = soul.voice.kokoro_speed
    if soul.voice.kokoro_voice is not None: voice_overrides['kokoro_voice'] = soul.voice.kokoro_voice

    if voice_overrides:
        merged['ai']['voice_overrides'] = voice_overrides

    return merged
