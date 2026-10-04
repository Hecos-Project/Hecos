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
            p_dump = preset.model_dump(exclude_unset=True)
            for k in ['temperature', 'top_p', 'repeat_penalty', 'num_predict', 'num_ctx', 'max_tokens']:
                if k in p_dump: backend_dict[k] = p_dump[k]
            
    # 2. Apply Inline Overrides (takes precedence)
    inf_dump = soul.inference.model_dump(exclude_unset=True)
    for k in ['temperature', 'top_p', 'repeat_penalty', 'num_predict', 'num_ctx', 'max_tokens', 'n_gpu_layers']:
        if k in inf_dump: backend_dict[k] = inf_dump[k]

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
    v_dump = soul.voice.model_dump(exclude_unset=True)
    
    voice_keys = [
        'xtts_preset', 'xtts_temperature', 'xtts_repetition_penalty', 'xtts_top_k', 
        'xtts_top_p', 'xtts_speed', 'xtts_length_penalty', 'xtts_speaker_wav',
        'piper_speed', 'piper_noise_scale', 'piper_noise_w',
        'kokoro_speed', 'kokoro_voice'
    ]
    for k in voice_keys:
        if k in v_dump:
            voice_overrides[k] = v_dump[k]

    if voice_overrides:
        merged['ai']['voice_overrides'] = voice_overrides

    return merged
