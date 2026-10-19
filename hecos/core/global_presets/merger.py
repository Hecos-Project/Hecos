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

    if soul.persona.use_global_direct_instructions is not None:
        if 'ai' not in merged: merged['ai'] = {}
        merged['ai']['use_global_direct_instructions'] = soul.persona.use_global_direct_instructions

    if soul.persona.use_global_safety_instructions is not None:
        if 'ai' not in merged: merged['ai'] = {}
        merged['ai']['use_global_safety_instructions'] = soul.persona.use_global_safety_instructions

    if soul.persona.custom_instructions is not None:
        if 'ai' not in merged: merged['ai'] = {}
        merged['ai']['custom_instructions'] = soul.persona.custom_instructions

    if soul.persona.user_notes is not None:
        if 'ai' not in merged: merged['ai'] = {}
        merged['ai']['user_notes'] = soul.persona.user_notes

    if soul.persona.send_notes_to_ai is not None:
        if 'ai' not in merged: merged['ai'] = {}
        merged['ai']['send_notes_to_ai'] = soul.persona.send_notes_to_ai

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
        'xtts_preset', 'xtts_inference_preset', 'xtts_temperature', 'xtts_repetition_penalty', 'xtts_top_k', 
        'xtts_top_p', 'xtts_speed', 'xtts_length_penalty', 'xtts_speaker_wav',
        'piper_speed', 'piper_noise_scale', 'piper_noise_w',
        'kokoro_speed', 'kokoro_voice', 'kokoro_volume', 'kokoro_normalize',
        'fish_preset', 'fish_inference_preset', 'fish_api_url', 'fish_reference_audio', 'fish_reference_text',
        'fish_temperature', 'fish_top_p', 'fish_repetition_penalty', 'fish_max_new_tokens',
        'fish_chunk_length', 'fish_seed', 'fish_normalize', 'fish_use_memory_cache', 'fish_reference_id'
    ]
    for k in voice_keys:
        if k in v_dump:
            voice_overrides[k] = v_dump[k]

    # Resolve Fish Speech preset defaults and inference preset if specified
    try:
        from hecos.core.audio.device_manager import get_audio_config
        acfg = get_audio_config()
        f_presets = acfg.get("fish_speech_presets", {})
        f_inf_presets = acfg.get("fish_speech_inference_presets", {})

        inf_preset_name = soul.voice.fish_inference_preset
        if soul.voice.fish_preset:
            f_p = f_presets.get(soul.voice.fish_preset)
            if f_p:
                if 'fish_reference_audio' not in voice_overrides and f_p.get('reference_audio'):
                    voice_overrides['fish_reference_audio'] = f_p['reference_audio']
                if 'fish_reference_text' not in voice_overrides and f_p.get('reference_text'):
                    voice_overrides['fish_reference_text'] = f_p['reference_text']
                if 'fish_reference_id' not in voice_overrides and f_p.get('reference_id'):
                    voice_overrides['fish_reference_id'] = f_p['reference_id']
                if not inf_preset_name and f_p.get('inference_preset'):
                    inf_preset_name = f_p['inference_preset']

        if inf_preset_name and inf_preset_name in f_inf_presets:
            inf_p = f_inf_presets[inf_preset_name]
            if 'fish_temperature' not in voice_overrides and inf_p.get('temperature') is not None:
                voice_overrides['fish_temperature'] = inf_p['temperature']
            if 'fish_top_p' not in voice_overrides and inf_p.get('top_p') is not None:
                voice_overrides['fish_top_p'] = inf_p['top_p']
            if 'fish_repetition_penalty' not in voice_overrides and inf_p.get('repetition_penalty') is not None:
                voice_overrides['fish_repetition_penalty'] = inf_p['repetition_penalty']
            if 'fish_max_new_tokens' not in voice_overrides and inf_p.get('max_new_tokens') is not None:
                voice_overrides['fish_max_new_tokens'] = inf_p['max_new_tokens']
            if 'fish_chunk_length' not in voice_overrides and inf_p.get('chunk_length') is not None:
                voice_overrides['fish_chunk_length'] = inf_p['chunk_length']
            if 'fish_normalize' not in voice_overrides and inf_p.get('normalize') is not None:
                voice_overrides['fish_normalize'] = inf_p['normalize']
            if 'fish_use_memory_cache' not in voice_overrides and inf_p.get('use_memory_cache') is not None:
                voice_overrides['fish_use_memory_cache'] = inf_p['use_memory_cache']

        if soul.voice.fish_preset:
            f_p = f_presets.get(soul.voice.fish_preset)
            if f_p:
                if 'fish_temperature' not in voice_overrides and f_p.get('temperature') is not None:
                    voice_overrides['fish_temperature'] = f_p['temperature']
                if 'fish_top_p' not in voice_overrides and f_p.get('top_p') is not None:
                    voice_overrides['fish_top_p'] = f_p['top_p']
                if 'fish_repetition_penalty' not in voice_overrides and f_p.get('repetition_penalty') is not None:
                    voice_overrides['fish_repetition_penalty'] = f_p['repetition_penalty']
                if 'fish_max_new_tokens' not in voice_overrides and f_p.get('max_new_tokens') is not None:
                    voice_overrides['fish_max_new_tokens'] = f_p['max_new_tokens']
                if 'fish_chunk_length' not in voice_overrides and f_p.get('chunk_length') is not None:
                    voice_overrides['fish_chunk_length'] = f_p['chunk_length']
                if 'fish_normalize' not in voice_overrides and f_p.get('normalize') is not None:
                    voice_overrides['fish_normalize'] = f_p['normalize']
                if 'fish_use_memory_cache' not in voice_overrides and f_p.get('use_memory_cache') is not None:
                    voice_overrides['fish_use_memory_cache'] = f_p['use_memory_cache']
    except Exception as e:
        logger.warning(f"[GlobalPresets] Error applying fish presets: {e}")

    if voice_overrides:
        merged['ai']['voice_overrides'] = voice_overrides

    return merged
