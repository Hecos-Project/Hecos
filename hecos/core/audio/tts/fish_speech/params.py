"""
MODULE: Fish Speech TTS - Parameter Resolution
DESCRIPTION: Handles parameter resolution, preset lookups (configuration presets and
             modular inference presets), companion transcript auto-loading,
             and session override merging.
"""

import os
from typing import NamedTuple, Optional
from hecos.core.logging import logger


def get_project_root() -> str:
    current_file = os.path.abspath(__file__)
    # Up from hecos/core/audio/tts/fish_speech/params.py -> root
    return os.path.abspath(os.path.join(current_file, "..", "..", "..", "..", ".."))


class FishSpeechParams(NamedTuple):
    api_url: str
    api_key: str
    ref_audio: str
    ref_text: str
    temperature: float
    top_p: float
    repetition_penalty: float
    max_new_tokens: int
    chunk_sentences: bool
    chunk_length: int = 200
    seed: int = 0
    normalize: bool = True
    use_memory_cache: bool = True
    reference_id: str = ""
    volume: float = 1.0


def resolve_fish_params(kwargs: dict) -> FishSpeechParams:
    """
    Resolves Fish Speech parameters merging global audio config, configuration presets,
    inference presets, companion transcripts, and session overrides.

    Returns:
        FishSpeechParams (NamedTuple compatible with tuple unpacking)
    """
    from hecos.core.audio.device_manager import get_audio_config
    acfg = get_audio_config()
    cfg = acfg.get("fish_speech", {})

    api_url = cfg.get("api_url", "http://127.0.0.1:8080/v1/tts").strip() or "http://127.0.0.1:8080/v1/tts"
    api_key = cfg.get("api_key", "").strip()
    reference_id = cfg.get("reference_id", "").strip()
    ref_audio = cfg.get("reference_audio", "").strip()
    ref_text = cfg.get("reference_text", "").strip()
    temperature = float(cfg.get("temperature", 0.7))
    top_p = float(cfg.get("top_p", 0.7))
    repetition_penalty = float(cfg.get("repetition_penalty", 1.2))
    max_new_tokens = int(cfg.get("max_new_tokens", 1024))
    chunk_sentences = bool(cfg.get("chunk_sentences", True))
    chunk_length = int(cfg.get("chunk_length", 200))
    seed = int(cfg.get("seed", 0))
    normalize = bool(cfg.get("normalize", True))
    use_memory_cache = bool(cfg.get("use_memory_cache", True))
    volume = float(cfg.get("volume", 1.0))

    f_inf_presets = acfg.get("fish_speech_inference_presets", {})
    current_inf_preset = cfg.get("current_inference_preset")
    if current_inf_preset and current_inf_preset in f_inf_presets:
        inf_data = f_inf_presets[current_inf_preset]
        if inf_data.get("temperature") is not None:
            temperature = float(inf_data["temperature"])
        if inf_data.get("top_p") is not None:
            top_p = float(inf_data["top_p"])
        if inf_data.get("repetition_penalty") is not None:
            repetition_penalty = float(inf_data["repetition_penalty"])
        if inf_data.get("max_new_tokens") is not None:
            max_new_tokens = int(inf_data["max_new_tokens"])
        if inf_data.get("chunk_length") is not None:
            chunk_length = int(inf_data["chunk_length"])
        if inf_data.get("seed") is not None:
            seed = int(inf_data["seed"])
        if inf_data.get("normalize") is not None:
            normalize = bool(inf_data["normalize"])
        if inf_data.get("use_memory_cache") is not None:
            use_memory_cache = bool(inf_data["use_memory_cache"])
        if inf_data.get("volume") is not None:
            volume = float(inf_data["volume"])

    # Check session overrides if provided
    session = kwargs.get("session_overrides") or {}
    if session:
        logger.debug("FISH_SPEECH", f"Applying session overrides: {list(session.keys())}")
        inf_preset_name = session.get("fish_inference_preset")

        # 1. Base Configuration Preset
        if session.get("fish_preset"):
            p_name = str(session["fish_preset"]).strip()
            f_presets = acfg.get("fish_speech_presets", {})
            if p_name in f_presets:
                preset_data = f_presets[p_name]
                if preset_data.get("reference_id"):
                    reference_id = str(preset_data["reference_id"]).strip()
                if preset_data.get("reference_audio"):
                    ref_audio = str(preset_data["reference_audio"]).strip()
                if preset_data.get("reference_text"):
                    ref_text = str(preset_data["reference_text"]).strip()
                if not inf_preset_name and preset_data.get("inference_preset"):
                    inf_preset_name = preset_data["inference_preset"]
                if preset_data.get("temperature") is not None:
                    temperature = float(preset_data["temperature"])
                if preset_data.get("top_p") is not None:
                    top_p = float(preset_data["top_p"])
                if preset_data.get("repetition_penalty") is not None:
                    repetition_penalty = float(preset_data["repetition_penalty"])
                if preset_data.get("max_new_tokens") is not None:
                    max_new_tokens = int(preset_data["max_new_tokens"])
                if preset_data.get("chunk_sentences") is not None:
                    chunk_sentences = bool(preset_data["chunk_sentences"])
                if preset_data.get("chunk_length") is not None:
                    chunk_length = int(preset_data["chunk_length"])
                if preset_data.get("seed") is not None:
                    seed = int(preset_data["seed"])
                if preset_data.get("normalize") is not None:
                    normalize = bool(preset_data["normalize"])
                if preset_data.get("use_memory_cache") is not None:
                    use_memory_cache = bool(preset_data["use_memory_cache"])
                if preset_data.get("volume") is not None:
                    volume = float(preset_data["volume"])
                logger.debug("FISH_SPEECH", f"Applied fish_preset '{p_name}'")

        # 2. Modular Inference Preset (overrides preset baseline parameters)
        if inf_preset_name and inf_preset_name in f_inf_presets:
            inf_data = f_inf_presets[inf_preset_name]
            if inf_data.get("temperature") is not None:
                temperature = float(inf_data["temperature"])
            if inf_data.get("top_p") is not None:
                top_p = float(inf_data["top_p"])
            if inf_data.get("repetition_penalty") is not None:
                repetition_penalty = float(inf_data["repetition_penalty"])
            if inf_data.get("max_new_tokens") is not None:
                max_new_tokens = int(inf_data["max_new_tokens"])
            if inf_data.get("chunk_length") is not None:
                chunk_length = int(inf_data["chunk_length"])
            if inf_data.get("seed") is not None:
                seed = int(inf_data["seed"])
            if inf_data.get("normalize") is not None:
                normalize = bool(inf_data["normalize"])
            if inf_data.get("use_memory_cache") is not None:
                use_memory_cache = bool(inf_data["use_memory_cache"])
            if inf_data.get("volume") is not None:
                volume = float(inf_data["volume"])
            logger.debug("FISH_SPEECH", f"Applied fish_inference_preset '{inf_preset_name}'")

        # 3. Explicit parameter overrides (highest priority)
        if session.get("fish_api_url"):
            api_url = str(session["fish_api_url"]).strip()
        if session.get("fish_reference_id"):
            reference_id = str(session["fish_reference_id"]).strip()
        if session.get("fish_reference_audio"):
            ref_audio = str(session["fish_reference_audio"]).strip()
        elif session.get("tts_voice") and session.get("tts_voice") != "default":
            ref_audio = str(session["tts_voice"]).strip()
        if session.get("fish_reference_text"):
            ref_text = str(session["fish_reference_text"]).strip()
        if session.get("fish_temperature") is not None:
            temperature = float(session["fish_temperature"])
        if session.get("fish_top_p") is not None:
            top_p = float(session["fish_top_p"])
        if session.get("fish_repetition_penalty") is not None:
            repetition_penalty = float(session["fish_repetition_penalty"])
        if session.get("fish_max_new_tokens") is not None:
            max_new_tokens = int(session["fish_max_new_tokens"])
        if session.get("fish_chunk_length") is not None:
            chunk_length = int(session["fish_chunk_length"])
        if session.get("fish_seed") is not None:
            seed = int(session["fish_seed"])
        if session.get("fish_normalize") is not None:
            normalize = bool(session["fish_normalize"])
        if session.get("fish_use_memory_cache") is not None:
            use_memory_cache = bool(session["fish_use_memory_cache"])
        if session.get("fish_chunk_sentences") is not None:
            chunk_sentences = bool(session["fish_chunk_sentences"])
        elif session.get("chunk_sentences") is not None:
            chunk_sentences = bool(session["chunk_sentences"])
        if session.get("fish_volume") is not None:
            volume = float(session["fish_volume"])
        elif session.get("volume") is not None:
            volume = float(session["volume"])

    # Resolve ref_audio path in assets/voice_clones if relative
    if ref_audio:
        if not os.path.isabs(ref_audio):
            root = get_project_root()
            candidates = [
                os.path.join(root, "assets", "voice_clones", ref_audio),
                os.path.join(root, "..", "hecos", "assets", "voice_clones", ref_audio),
                os.path.join(root, "hecos", "assets", "voice_clones", ref_audio),
            ]
            found_path = None
            for cand in candidates:
                cand_norm = os.path.normpath(cand)
                if os.path.isfile(cand_norm):
                    found_path = cand_norm
                    break

            if found_path:
                ref_audio = found_path
            else:
                logger.warning("FISH_SPEECH", f"Reference audio not found in library: '{ref_audio}'")
                ref_audio = ""
        elif not os.path.exists(ref_audio):
            logger.warning("FISH_SPEECH", f"Explicit reference audio path not found: '{ref_audio}'")
            ref_audio = ""

    # Auto-load companion transcript (.txt) if no text was explicitly provided
    if ref_audio and not ref_text:
        txt_path = os.path.splitext(ref_audio)[0] + ".txt"
        if os.path.exists(txt_path):
            try:
                with open(txt_path, "r", encoding="utf-8") as tf:
                    ref_text = tf.read().strip()
                logger.debug("FISH_SPEECH", f"Loaded companion transcript ({len(ref_text)} chars) for '{os.path.basename(ref_audio)}'")
            except Exception as te:
                logger.warning("FISH_SPEECH", f"Could not read companion transcript: {te}")

    ref_basename = os.path.basename(ref_audio) if ref_audio else (f"ID:{reference_id}" if reference_id else "None (Server default voice)")
    logger.info(
        "FISH_SPEECH",
        f"Params resolved: api_url='{api_url}', cloud_mode={bool(api_key)}, "
        f"ref='{ref_basename}', temp={temperature}, top_p={top_p}, "
        f"rep_pen={repetition_penalty}, max_tokens={max_new_tokens}, chunk_len={chunk_length}, "
        f"norm={normalize}, cache={use_memory_cache}, seed={seed}, vol={volume}"
    )

    return FishSpeechParams(
        api_url=api_url,
        api_key=api_key,
        ref_audio=ref_audio,
        ref_text=ref_text,
        temperature=temperature,
        top_p=top_p,
        repetition_penalty=repetition_penalty,
        max_new_tokens=max_new_tokens,
        chunk_sentences=chunk_sentences,
        chunk_length=chunk_length,
        seed=seed,
        normalize=normalize,
        use_memory_cache=use_memory_cache,
        reference_id=reference_id,
        volume=volume
    )
