"""
Voice Forge - Full DSP Pipeline Orchestrator
Coordinates source generation, WORLD decomposition, physical vocal tract sculpting,
texture modulation, acoustic equalization, and resynthesis.
"""

import hashlib
import os
import time
import threading
from collections import OrderedDict
from typing import Any, List, Tuple, Optional, Callable
import numpy as np

from .recipe import VoiceRecipe, compute_recipe_dsp_flags
from .world_vocoder import vocoder
from .pitch_formant import shift_pitch, adjust_dynamics, warp_formants
from .texture import apply_breathiness, apply_roughness, apply_tremolo
from .acoustic_eq import apply_acoustic_eq
from .morphing import blend_acoustic_features
from .execution_trace import record_trace_dsp, record_trace_routing, suppress_trace_chunks
from .log_utils import _vf_log
from .engines import (
    adjust_dsp_for_emotion,
    generate_tts_source_audio,
    has_expressive_tags,
    has_non_pause_tags,
    normalize_emotion_style,
    propagate_style_across_chunks,
    split_on_pauses,
    split_on_tag_transitions,
    strip_expressive_tags,
)
from .engines.tag_processor import update_active_style
from .engines.text_chunker import concat_timeline_segments, split_text_into_chunks
from .sources_audio import load_audio_file, save_audio_file
from .multilang_corpus import get_calibration_sample
from .whisper_dsp import (
    apply_whisper_dsp,
    classify_whisper_directive,
    normalize_whisper_mode,
)


def is_fish_expressive_available() -> bool:
    """Returns True when local Fish Speech S2-Pro or Fish Cloud can perform expressive tags."""
    try:
        from hecos.core.audio.tts.fish_speech_engine import FishSpeechEngine
        if FishSpeechEngine.is_available() and FishSpeechEngine.model_ready():
            return True
    except Exception:
        pass
    try:
        from hecos.core.audio.tts.fish_speech_daemon import FishSpeechDaemon
        daemon = FishSpeechDaemon.get_instance()
        host, port = daemon._resolve_target()
        if daemon.is_healthy(host, port, timeout=0.6) or daemon.is_port_listening(host, port):
            return True
    except Exception:
        pass
    return False


def _effective_dsp_params(recipe: VoiceRecipe) -> Tuple[float, float, float]:
    """Resolves effective (pitch_dynamics, breathiness, roughness) honoring non-Fish emotion DSP deltas."""
    if recipe.source_type == "synthetic_fish":
        return float(recipe.pitch_dynamics), float(recipe.breathiness), float(recipe.roughness)
    return adjust_dsp_for_emotion(
        recipe.pitch_dynamics,
        recipe.breathiness,
        recipe.roughness,
        getattr(recipe, "emotion_style", "balanced"),
    )


def requires_world_sculpt(
    recipe: VoiceRecipe,
    eff_dyn: Optional[float] = None,
    eff_breath: Optional[float] = None,
    eff_rough: Optional[float] = None,
) -> bool:
    """Returns True when any spectral, pitch, formant, texture, or morph control deviates from neutral."""
    if eff_dyn is None or eff_breath is None or eff_rough is None:
        eff_dyn, eff_breath, eff_rough = _effective_dsp_params(recipe)
    return compute_recipe_dsp_flags(
        recipe, eff_dyn=eff_dyn, eff_breath=eff_breath, eff_rough=eff_rough
    )["uses_world"]


def requires_eq(recipe: VoiceRecipe) -> bool:
    """Returns True when any 4-band acoustic EQ gain deviates from 0 dB."""
    return compute_recipe_dsp_flags(recipe)["uses_eq"]


def is_neutral_sculpt(recipe: VoiceRecipe) -> bool:
    """Returns True when neither WORLD sculpting nor 4-band EQ is needed."""
    return not requires_world_sculpt(recipe) and not requires_eq(recipe)


class ForgePipeline:
    def __init__(self, source_cache_size: int = 12):
        self.vocoder = vocoder
        self._source_cache: OrderedDict = OrderedDict()
        self._source_cache_size = max(1, int(source_cache_size))
        self._source_cache_lock = threading.Lock()

    def _emit(
        self,
        progress_cb: Optional[Callable[[str, float, str], None]],
        phase: str,
        fraction: float,
        message: str,
    ) -> None:
        if progress_cb is not None:
            try:
                progress_cb(phase, max(0.0, min(1.0, float(fraction))), message)
            except Exception:
                pass

    def _build_source_cache_key(self, recipe: VoiceRecipe, ref_text: str) -> Optional[Tuple]:
        if getattr(recipe, "fresh_take", False):
            return None
        lang = (recipe.language or "en").lower()
        preset = getattr(recipe, "source_preset", None) or ""
        speaker = getattr(recipe, "source_speaker", None) or ""
        style = normalize_emotion_style(getattr(recipe, "emotion_style", None))
        inf_preset = str(getattr(recipe, "inference_preset", None) or "").strip()
        raw_inf_params = getattr(recipe, "inference_params", None) or {}
        inf_params_sig = tuple(sorted((str(k), repr(v)) for k, v in raw_inf_params.items())) if isinstance(raw_inf_params, dict) else ()
        if recipe.source_type == "synthetic_fish":
            seed = int(recipe.source_seed if recipe.source_seed is not None else 42)
            # Only vary cache by seed when running in seed mode (no preset/clone selected)
            eff_seed = seed if (not preset and speaker in ("", "default", "__seed__")) else 0
            w_mode = normalize_whisper_mode(getattr(recipe, "whisper_mode", None))
            w_lvl = classify_whisper_directive(ref_text, emotion_style=style)
            dual_sig = "dual_ref" if (w_mode == "dual_ref" and w_lvl in ("whisper", "low_voice")) else "single_ref"
            return ("synthetic_fish", ref_text, lang, preset, speaker, eff_seed, style, inf_preset, inf_params_sig, dual_sig)
        if recipe.source_type in ("synthetic_kokoro", "synthetic_piper", "synthetic_xtts"):
            return (recipe.source_type, ref_text, lang, preset, speaker, style, inf_preset, inf_params_sig)
        if recipe.source_type == "file" and recipe.source_file:
            try:
                abs_path = os.path.abspath(recipe.source_file)
                mtime = os.path.getmtime(abs_path)
                return ("file", abs_path, mtime)
            except OSError:
                return None
        return None

    def clear_source_cache(self) -> None:
        with self._source_cache_lock:
            self._source_cache.clear()
        _vf_log("debug", "ForgePipeline source audio cache cleared")

    def resolve_source(
        self,
        recipe: VoiceRecipe,
        custom_audio: Optional[np.ndarray] = None,
        fs: int = 44100,
        progress_cb: Optional[Callable[[str, float, str], None]] = None,
    ) -> Tuple[np.ndarray, int]:
        """Resolves the raw source audio based on recipe configuration (with LRU cache)."""
        if custom_audio is not None:
            self._emit(progress_cb, "source", 1.0, "Using provided custom source buffer")
            return custom_audio, fs

        # Check reference text; fallback to multilingual corpus if empty
        ref_text = recipe.reference_text.strip()
        if not ref_text:
            corpus_sample = get_calibration_sample(recipe.language, "narrative")
            ref_text = corpus_sample["text"]
            recipe.reference_text = ref_text

        cache_key = self._build_source_cache_key(recipe, ref_text)
        if cache_key is not None:
            with self._source_cache_lock:
                if cache_key in self._source_cache:
                    self._source_cache.move_to_end(cache_key)
                    cached_audio, cached_fs = self._source_cache[cache_key]
                    _vf_log("info", f"Source audio cache HIT for {recipe.source_type}")
                    self._emit(progress_cb, "source", 1.0, f"Loaded cached {recipe.source_type} source")
                    return cached_audio.copy(), cached_fs

        self._emit(progress_cb, "source", 0.05, f"Generating source audio ({recipe.source_type})...")
        inner_cb = (
            (lambda frac, msg: self._emit(progress_cb, "source", frac, msg))
            if progress_cb is not None else None
        )

        if recipe.source_type in ("synthetic_fish", "synthetic_kokoro", "synthetic_piper", "synthetic_xtts"):
            audio, out_fs = generate_tts_source_audio(recipe, ref_text, progress_cb=inner_cb)

        elif recipe.source_type == "file":
            if not recipe.source_file:
                raise ValueError("Source type is 'file' but source_file path is not specified.")
            self._emit(progress_cb, "source", 0.4, f"Loading source file {os.path.basename(recipe.source_file)}...")
            audio, out_fs = load_audio_file(recipe.source_file, target_sr=44100)
            self._emit(progress_cb, "source", 1.0, "Source audio file loaded")

        else:
            raise ValueError(f"Unknown source_type: {recipe.source_type}")

        if cache_key is not None and audio is not None and len(audio) > 0:
            with self._source_cache_lock:
                self._source_cache[cache_key] = (audio.copy(), out_fs)
                self._source_cache.move_to_end(cache_key)
                while len(self._source_cache) > self._source_cache_size:
                    self._source_cache.popitem(last=False)

        return audio, out_fs

    def _apply_post_whisper_dsp(
        self,
        recipe: VoiceRecipe,
        audio: np.ndarray,
        sample_rate: int,
        progress_cb: Optional[Callable[[str, float, str], None]] = None,
    ) -> np.ndarray:
        """Converts active [whisper]/[low voice] chunks physically when whisper_mode == 'dsp'."""
        w_mode = normalize_whisper_mode(getattr(recipe, "whisper_mode", None))
        if w_mode != "dsp":
            return audio
        w_level = classify_whisper_directive(
            recipe.reference_text or "",
            emotion_style=getattr(recipe, "emotion_style", None),
        )
        if w_level not in ("whisper", "low_voice"):
            return audio
        self._emit(progress_cb, "sculpt", 0.9, f"Applying same-voice PyWORLD {w_level}...")
        out = apply_whisper_dsp(audio, sr=sample_rate, level=w_level, vocoder=self.vocoder)
        record_trace_dsp(whisper_mode="dsp", whisper_dsp_level=w_level)
        _vf_log("info", f"Applied same-voice PyWORLD {w_level} DSP post-step for '{recipe.name}'")
        return out

    def process(
        self,
        recipe: VoiceRecipe,
        base_audio: Optional[np.ndarray] = None,
        fs: int = 44100,
        progress_cb: Optional[Callable[[str, float, str], None]] = None,
    ) -> Tuple[np.ndarray, int]:
        """
        Executes the full Voice Forge sculpting pipeline on the input recipe.
        Returns the finalized reference audio waveform and sample rate.
        """
        t_start = time.monotonic()
        _vf_log(
            "info",
            f"Pipeline start: recipe='{recipe.name}' (id={recipe.id}), "
            f"source={recipe.source_type}, lang={recipe.language}"
        )

        # 1. Resolve source audio
        audio, sample_rate = self.resolve_source(
            recipe,
            custom_audio=base_audio,
            fs=fs,
            progress_cb=progress_cb,
        )

        dur_src = len(audio) / float(sample_rate) if sample_rate > 0 else 0.0
        if getattr(recipe, "bypass_world", False):
            # Sculpt-First Auto-Clone: target timbre & EQ were baked into the clone reference WAV
            record_trace_dsp(
                dsp_mode="pure_neural_bypass",
                needs_world=False,
                needs_eq=False,
                effective_pitch_dynamics=float(recipe.pitch_dynamics),
                effective_breathiness=float(recipe.breathiness),
                effective_roughness=float(recipe.roughness),
            )
            self._emit(progress_cb, "analyze", 1.0, "Pure neural actor delivery (Sculpt-First clone)")
            self._emit(progress_cb, "sculpt", 1.0, "Skipping post-WORLD resynthesis to preserve vocal nuances")
            final_audio = self._apply_post_whisper_dsp(recipe, audio, sample_rate, progress_cb=progress_cb)
            dur_out = len(final_audio) / float(sample_rate) if sample_rate > 0 else 0.0
            self._emit(progress_cb, "synth", 1.0, f"Pure neural synthesis complete ({dur_out:.1f}s @ {sample_rate}Hz)")
            _vf_log("info", f"Pipeline pure-neural bypass complete in {time.monotonic() - t_start:.2f}s (output={dur_out:.2f}s)")
            return final_audio, sample_rate

        eff_dyn, eff_breath, eff_rough = _effective_dsp_params(recipe)
        needs_world = requires_world_sculpt(recipe, eff_dyn, eff_breath, eff_rough)
        needs_eq = requires_eq(recipe)
        record_trace_dsp(
            dsp_mode=(
                ("world_vocoder_plus_eq" if needs_eq else "world_vocoder")
                if needs_world
                else ("eq_only_world_bypass" if needs_eq else "neutral_world_bypass")
            ),
            needs_world=needs_world,
            needs_eq=needs_eq,
            effective_pitch_dynamics=float(eff_dyn),
            effective_breathiness=float(eff_breath),
            effective_roughness=float(eff_rough),
        )

        if not needs_world:
            self._emit(progress_cb, "analyze", 1.0, "Neutral timbre — bypassing WORLD resynthesis")
            self._emit(progress_cb, "sculpt", 1.0, "No pitch or formant warp active")
            if needs_eq:
                self._emit(progress_cb, "synth", 0.75, "Applying 4-band acoustic equalization...")
                final_audio = apply_acoustic_eq(
                    audio,
                    fs=sample_rate,
                    body_db=recipe.body_gain_db,
                    warmth_db=recipe.warmth_gain_db,
                    presence_db=recipe.presence_gain_db,
                    air_db=recipe.air_gain_db,
                )
            else:
                final_audio = audio
            final_audio = self._apply_post_whisper_dsp(recipe, final_audio, sample_rate, progress_cb=progress_cb)
            elapsed = time.monotonic() - t_start
            dur = len(final_audio) / float(sample_rate) if sample_rate > 0 else 0.0
            _vf_log("info", f"Pipeline neutral-bypass complete in {elapsed:.2f}s (eq={needs_eq}, output={dur:.2f}s)")
            self._emit(progress_cb, "synth", 1.0, f"Synthesis complete ({dur:.1f}s @ {sample_rate}Hz)")
            return final_audio, sample_rate

        # 2. Decompose into acoustic features via WORLD Vocoder
        self._emit(progress_cb, "analyze", 0.15, "Decomposing F0, spectral envelope & aperiodicity (WORLD)...")
        f0, timeaxis, sp, ap = self.vocoder.analyze(audio, fs=sample_rate, use_cache=True)
        self._emit(progress_cb, "analyze", 1.0, "WORLD vocal tract decomposition complete")

        # 3. Optional Spectral Morphing with Source B
        self._emit(progress_cb, "sculpt", 0.1, "Applying vocal tract sculpting & modulation...")
        if recipe.blend_source_file and recipe.blend_ratio > 0.001:
            try:
                audio_b, sr_b = load_audio_file(recipe.blend_source_file, target_sr=sample_rate)
                f0_b, _, sp_b, ap_b = self.vocoder.analyze(audio_b, fs=sr_b, use_cache=True)
                f0, sp, ap = blend_acoustic_features(f0, sp, ap, f0_b, sp_b, ap_b, recipe.blend_ratio)
                _vf_log("debug", f"Applied spectral morph ratio={recipe.blend_ratio:.2f} with '{recipe.blend_source_file}'")
            except Exception as e:
                _vf_log("warning", f"Spectral morph with '{recipe.blend_source_file}' failed, continuing with primary source: {e}")

        # 4. Pitch & Intonation Dynamics
        if abs(recipe.pitch_semitones) > 1e-4:
            f0 = shift_pitch(f0, recipe.pitch_semitones)

        if abs(eff_dyn - 1.0) > 1e-4:
            f0 = adjust_dynamics(f0, eff_dyn)

        self._emit(progress_cb, "sculpt", 0.55, "Warping vocal tract formants & laryngeal texture...")

        # 5. Vocal Tract Length / Formant Warping
        if abs(recipe.vocal_tract_ratio - 1.0) > 1e-4:
            sp = warp_formants(sp, recipe.vocal_tract_ratio)

        # 6. Physical Texture (Breath, Roughness, Tremolo)
        if eff_breath > 1e-4:
            ap = apply_breathiness(ap, eff_breath)

        if eff_rough > 1e-4:
            f0, ap = apply_roughness(f0, ap, eff_rough)

        if recipe.tremolo > 1e-4:
            f0 = apply_tremolo(f0, timeaxis, recipe.tremolo)

        self._emit(progress_cb, "sculpt", 1.0, "Vocal tract & texture sculpting complete")

        # 7. Resynthesis via WORLD Vocoder
        self._emit(progress_cb, "synth", 0.25, "Resynthesizing waveform via WORLD vocoder...")
        resynth = self.vocoder.synthesize(f0, sp, ap, fs=sample_rate)

        # 8. 4-Band Acoustic Equalization (Body, Warmth, Presence, Air)
        if needs_eq:
            self._emit(progress_cb, "synth", 0.75, "Applying 4-band acoustic equalization...")
            final_audio = apply_acoustic_eq(
                resynth,
                fs=sample_rate,
                body_db=recipe.body_gain_db,
                warmth_db=recipe.warmth_gain_db,
                presence_db=recipe.presence_gain_db,
                air_db=recipe.air_gain_db,
            )
        else:
            final_audio = resynth
        final_audio = self._apply_post_whisper_dsp(recipe, final_audio, sample_rate, progress_cb=progress_cb)
        elapsed = time.monotonic() - t_start
        dur = len(final_audio) / float(sample_rate) if sample_rate > 0 else 0.0
        _vf_log("info", f"Pipeline complete in {elapsed:.2f}s (output={dur:.2f}s @ {sample_rate}Hz)")
        self._emit(progress_cb, "synth", 1.0, f"Synthesis complete ({dur:.1f}s @ {sample_rate}Hz)")

        return final_audio, sample_rate

    def _resolve_clone_reference_wav(
        self,
        recipe: VoiceRecipe,
        progress_cb: Optional[Callable[[str, float, str], None]] = None,
    ) -> Tuple[str, str]:
        """
        Generates or reuses a Sculpt-First foundation WAV + transcript for zero-shot
        expressive cloning (e.g. sculpting Sharon/Michael's pitch & formants BEFORE
        Fish S2-Pro performs [laughing]/[sigh], so S2-Pro delivers pure neural nuances).
        """
        clean_ref = strip_expressive_tags(recipe.reference_text or "")
        if len(clean_ref) < 25:
            clean_ref = get_calibration_sample(recipe.language, "narrative")["text"]

        sculpt_dyn = max(1.22, float(recipe.pitch_dynamics))
        key_raw = "|".join([
            "v2",
            str(recipe.source_type or ""),
            str(recipe.source_preset or ""),
            str(recipe.source_speaker or ""),
            str(recipe.language or "en").lower(),
            clean_ref,
            f"p={recipe.pitch_semitones:.3f}",
            f"d={sculpt_dyn:.3f}",
            f"t={recipe.vocal_tract_ratio:.3f}",
            f"b={recipe.breathiness:.3f}",
            f"r={recipe.roughness:.3f}",
            f"m={recipe.tremolo:.3f}",
            f"eq={recipe.body_gain_db:.2f},{recipe.warmth_gain_db:.2f},{recipe.presence_gain_db:.2f},{recipe.air_gain_db:.2f}",
            str(recipe.blend_source_file or ""),
            f"br={recipe.blend_ratio:.3f}",
        ])
        key_hash = hashlib.sha256(key_raw.encode("utf-8")).hexdigest()[:16]

        try:
            from ..library.storage import PREVIEWS_DIR
            cache_dir = PREVIEWS_DIR / "vf_clone_cache"
        except Exception:
            import tempfile
            from pathlib import Path
            cache_dir = Path(tempfile.gettempdir()) / "vf_clone_cache"

        cache_dir.mkdir(parents=True, exist_ok=True)
        wav_path = cache_dir / f"vf_clone_v2_{key_hash}.wav"
        txt_path = cache_dir / f"vf_clone_v2_{key_hash}.txt"

        if not wav_path.is_file() or wav_path.stat().st_size < 1024:
            # Generate animated foundation with theatrical engine boost + sculpt BEFORE Fish S2-Pro cloning
            ref_recipe = recipe.model_copy(update={
                "reference_text": clean_ref,
                "emotion_style": "theatrical",
                "pitch_dynamics": sculpt_dyn,
                "bypass_world": False,
                "fresh_take": False,
            })
            with suppress_trace_chunks():
                audio, sr = self.process(ref_recipe, progress_cb=progress_cb)
            save_audio_file(audio, str(wav_path), fs=sr)
            txt_path.write_text(clean_ref, encoding="utf-8")
            _vf_log(
                "info",
                f"Cached Sculpt-First clone reference '{wav_path.name}' from {recipe.source_type} "
                f"(pitch={recipe.pitch_semitones:+.1f}st, tract={recipe.vocal_tract_ratio:.2f}x, "
                f"{len(audio) / float(sr):.2f}s @ {sr}Hz)",
            )
        elif not txt_path.is_file():
            txt_path.write_text(clean_ref, encoding="utf-8")

        return str(wav_path), clean_ref

    def _prepare_production_recipe(
        self,
        recipe: VoiceRecipe,
        script_text: str,
        clone_engine: Optional[str] = None,
        progress_cb: Optional[Callable[[str, float, str], None]] = None,
    ) -> VoiceRecipe:
        """
        Prepares a recipe for Production Mode:
        - Uploaded WAV files route into Fish/XTTS zero-shot cloning for arbitrary text.
        - Non-tag TTS foundations (Kokoro, Piper, XTTS) with expressive [tags] automatically
          route through Fish Speech S2-Pro zero-shot cloning using their Sculpt-First WAV so
          S2-Pro performs sighs, laughter, and emotion natively without post-WORLD flattening.
        """
        if recipe.source_type in ("synthetic_kokoro", "synthetic_piper", "synthetic_xtts"):
            if has_non_pause_tags(script_text):
                prefer_fish = (clone_engine or "synthetic_fish").strip().lower() == "synthetic_fish"
                if prefer_fish and is_fish_expressive_available():
                    ref_wav, ref_txt = self._resolve_clone_reference_wav(recipe, progress_cb=progress_cb)
                    _vf_log(
                        "info",
                        f"Expressive tags detected for {recipe.source_type}; routing '{recipe.name}' "
                        "through Sculpt-First Fish Speech S2-Pro (pure-neural delivery, post-WORLD skipped)",
                    )
                    record_trace_routing(
                        routing_mode="sculpt_first_fish_clone",
                        original_source_type=recipe.source_type,
                        clone_reference_wav=ref_wav,
                        clone_reference_text=ref_txt,
                    )
                    return recipe.model_copy(update={
                        "source_type": "synthetic_fish",
                        "source_preset": None,
                        "source_speaker": ref_wav,
                        "clone_reference_text": ref_txt,
                        "inference_preset": None,
                        "inference_params": {},
                        "bypass_world": True,
                    })
                _vf_log(
                    "warning",
                    f"Expressive tags detected for {recipe.source_type} but Fish Speech S2-Pro is "
                    "unavailable; stripping bracketed vocal cues cleanly",
                )
            record_trace_routing(routing_mode="direct_foundation", original_source_type=recipe.source_type)
            return recipe

        if recipe.source_type != "file":
            # For Fish S2-Pro in seed/clone/preset mode: if the script contains expressive tags,
            # ALWAYS bypass the WORLD vocoder unconditionally — regardless of DSP slider positions.
            # WORLD re-synthesis flattens pitch/aperiodicity dynamics that S2-Pro natively encodes
            # in the signal (excited energy, whisper breathiness, laughing pitch variance).
            # Even with all sliders at zero, tiny float deltas in emotion profiles can trigger
            # requires_world_sculpt(); we skip that check entirely for Fish + tags.
            if recipe.source_type == "synthetic_fish" and has_non_pause_tags(script_text):
                record_trace_routing(
                    routing_mode="fish_seed_tag_bypass_world",
                    original_source_type=recipe.source_type,
                )
                _vf_log(
                    "info",
                    f"Fish S2-Pro with expressive tags — bypass_world=True (unconditional) "
                    f"to preserve [excited]/[whisper]/[laughing] neural dynamics "
                    f"(pitch={recipe.pitch_semitones:+.2f}st, dyn={recipe.pitch_dynamics:.2f}, "
                    f"tract={recipe.vocal_tract_ratio:.2f}x, breath={recipe.breathiness:.3f}, "
                    f"rough={recipe.roughness:.3f})",
                )
                return recipe.model_copy(update={"bypass_world": True})
            record_trace_routing(routing_mode="direct_foundation", original_source_type=recipe.source_type)
            return recipe
        if not recipe.source_file or not os.path.isfile(recipe.source_file):
            raise FileNotFoundError("Source type is 'file' but no valid audio file is selected.")

        norm_script = " ".join((script_text or "").split())
        norm_ref = " ".join((recipe.reference_text or "").split())
        has_any_tags = has_expressive_tags(script_text or "")
        if not norm_script or (norm_script == norm_ref and not has_any_tags):
            record_trace_routing(routing_mode="direct_file_sculpt", original_source_type="file")
            return recipe

        chosen = (clone_engine or "").strip().lower()
        if chosen not in ("synthetic_fish", "synthetic_xtts"):
            chosen = ""
            try:
                from hecos.core.audio.tts.fish_speech_daemon import FishSpeechDaemon
                daemon = FishSpeechDaemon.get_instance()
                host, port = daemon._resolve_target()
                if daemon.is_healthy(host, port, timeout=1.0) or daemon.is_port_listening(host, port):
                    chosen = "synthetic_fish"
            except Exception:
                pass
            if not chosen:
                try:
                    from hecos.core.audio.tts.xtts_engine import get_engine as get_xtts
                    if get_xtts().is_available():
                        chosen = "synthetic_xtts"
                except Exception:
                    pass
            if not chosen:
                chosen = "synthetic_fish"

        # Only treat recipe.reference_text as a spoken WAV transcript when it differs
        # from the target script and does not contain expressive [tags].
        raw_ref = recipe.reference_text or ""
        if norm_ref and norm_ref != norm_script and not has_expressive_tags(raw_ref):
            clean_ref = " ".join(strip_expressive_tags(raw_ref).split())
        else:
            clean_ref = ""

        cloned = recipe.model_copy(update={
            "source_type": chosen,
            "source_preset": None,
            "source_speaker": f"wav:{recipe.source_file}" if chosen == "synthetic_xtts" else recipe.source_file,
            "clone_reference_text": clean_ref or None,
        })
        if chosen == "synthetic_fish" and has_non_pause_tags(script_text or "") and requires_world_sculpt(cloned):
            cloned = cloned.model_copy(update={"bypass_world": True})
            _vf_log(
                "info",
                f"Uploaded WAV '{os.path.basename(recipe.source_file)}' uses expressive tags; "
                "bypassing post-Fish PyWORLD sculpt so S2-Pro dynamics are preserved",
            )
        record_trace_routing(
            routing_mode="upload_zero_shot_clone",
            original_source_type="file",
            routed_engine=chosen,
            clone_reference_wav=recipe.source_file,
            clone_reference_text=clean_ref,
        )
        _vf_log(
            "info",
            f"Production script using uploaded file routed to zero-shot '{chosen}' for '{recipe.source_file}'",
        )
        return cloned

    def _build_production_timeline(
        self,
        clean_text: str,
        supports_tags: bool,
        max_chars: int = 240,
    ) -> List[Tuple[str, Any]]:
        """Builds an ordered timeline of speech chunks and explicit silence durations."""
        raw_segments = split_on_pauses(clean_text)
        timeline: List[Tuple[str, Any]] = []
        active_style = ""

        for kind, val in raw_segments:
            if kind == "silence":
                timeline.append(("silence", float(val)))
                continue

            block_text = str(val or "").strip()
            if not block_text:
                continue

            if not supports_tags:
                block_text = strip_expressive_tags(block_text)
                if not block_text:
                    continue
                for chunk in split_text_into_chunks(block_text, max_chars=max_chars):
                    timeline.append(("speech", chunk))
                continue

            tag_clauses = split_on_tag_transitions(block_text)
            split_chunks: List[str] = []
            for clause in tag_clauses:
                split_chunks.extend(split_text_into_chunks(clause, max_chars=max_chars))
            styled_chunks = propagate_style_across_chunks(split_chunks, initial_style=active_style)
            for chunk in styled_chunks:
                timeline.append(("speech", chunk))
                active_style = update_active_style(chunk, active_style)

        return timeline

    def process_long_text(
        self,
        recipe: VoiceRecipe,
        script_text: str,
        pause_sec: float = 0.22,
        clone_engine: Optional[str] = None,
        fresh_take: bool = False,
        progress_cb: Optional[Callable[[str, float, str], None]] = None,
    ) -> Tuple[np.ndarray, int]:
        """
        Synthesizes and acoustically sculpts arbitrary-length production text
        with expressive directive tags, deterministic pauses, and smooth concatenation.
        """
        clean_text = (script_text or "").strip() or (recipe.reference_text or "").strip()
        if not clean_text:
            clean_text = get_calibration_sample(recipe.language, "narrative")["text"]

        eff_recipe = self._prepare_production_recipe(
            recipe,
            clean_text,
            clone_engine=clone_engine,
            progress_cb=progress_cb,
        )
        eff_recipe = eff_recipe.model_copy(update={"fresh_take": bool(fresh_take)})
        if eff_recipe.source_type == "file":
            return self.process(eff_recipe, progress_cb=progress_cb)

        # In Fish S2-Pro zero-shot seed mode (no clone WAV, no preset), splitting on tag
        # transitions generates a DIFFERENT random speaker per chunk, since each synthesize_fish()
        # call with an empty reference list picks a random new voice from the seed alone.
        # To preserve a single speaker identity across the entire text with inline expressive
        # tags, we send the whole text in one coherent S2-Pro pass — exactly as fish_speech_engine
        # does in its zero-shot path (≤450 chars guard already handled upstream).
        _is_zero_shot_seed = (
            eff_recipe.source_type == "synthetic_fish"
            and not (getattr(eff_recipe, "source_preset", None) or "").strip()
            and not (
                getattr(eff_recipe, "source_speaker", None) or ""
            ).strip().replace("default", "").replace("__seed__", "")
        )
        if _is_zero_shot_seed:
            # Single-pass: preserve speaker identity and tag dynamics across all expressive markers.
            single = eff_recipe.model_copy(update={"reference_text": clean_text})
            return self.process(single, progress_cb=progress_cb)

        # Fish Speech handles [tag] transitions natively via its own chunk_length chunker.
        # Splitting on 240-char boundaries here would send each chunk as a separate TTS call,
        # making S2-Pro pick a different speaker identity per chunk and completely ignoring
        # cross-chunk tag continuity. When tags are present and the source is Fish, always
        # send the full text in a single pass and let Fish Speech do its own internal chunking.
        _is_fish_with_tags = (
            eff_recipe.source_type == "synthetic_fish"
            and has_non_pause_tags(clean_text)
        )
        if _is_fish_with_tags:
            _vf_log(
                "info",
                f"Fish S2-Pro with expressive tags — single-pass synthesis to preserve "
                f"voice identity and cross-tag dynamics (bypassing VF 240-char chunker)",
            )
            record_trace_routing(
                routing_mode="fish_tag_single_pass",
                original_source_type=eff_recipe.source_type,
            )
            single = eff_recipe.model_copy(update={"reference_text": clean_text})
            return self.process(single, progress_cb=progress_cb)

        supports_tags = eff_recipe.source_type == "synthetic_fish"
        timeline_plan = self._build_production_timeline(clean_text, supports_tags=supports_tags, max_chars=240)
        speech_indices = [idx for idx, (k, _) in enumerate(timeline_plan) if k == "speech"]

        if not speech_indices:
            total_sil = sum(float(v) for k, v in timeline_plan if k == "silence")
            dur_s = max(0.35, total_sil)
            self._emit(progress_cb, "synth", 1.0, f"Generated silence beat ({dur_s:.2f}s)")
            return np.zeros(int(round(dur_s * 44100)), dtype=np.float64), 44100

        if len(speech_indices) == 1 and len(timeline_plan) == 1:
            single = eff_recipe.model_copy(update={"reference_text": str(timeline_plan[0][1])})
            return self.process(single, progress_cb=progress_cb)

        total = len(speech_indices)
        _vf_log("info", f"Long-text production pipeline: {total} speech chunk(s), {len(timeline_plan)} timeline items for '{eff_recipe.name}'")
        rendered_timeline: List[Tuple[str, Any]] = []
        sample_rate = 44100
        done_chunks = 0

        for kind, val in timeline_plan:
            if kind == "silence":
                rendered_timeline.append(("silence", float(val)))
                continue

            idx = done_chunks
            done_chunks += 1
            base_frac = idx / float(total)
            span_frac = 1.0 / float(total)

            def _chunk_cb(phase: str, frac: float, msg: str, _b=base_frac, _s=span_frac, _i=idx) -> None:
                if progress_cb is not None:
                    overall = max(0.0, min(0.99, _b + max(0.0, min(1.0, frac)) * _s))
                    try:
                        progress_cb(phase, overall, f"Chunk {_i + 1}/{total}: {msg}")
                    except Exception:
                        pass

            sub_recipe = eff_recipe.model_copy(update={"reference_text": str(val)})
            seg_audio, seg_sr = self.process(sub_recipe, progress_cb=_chunk_cb)
            sample_rate = seg_sr
            rendered_timeline.append(("audio", seg_audio))

        combined = concat_timeline_segments(rendered_timeline, fs=sample_rate, sentence_pause_sec=pause_sec)
        self._emit(progress_cb, "synth", 1.0, f"Joined {total} chunks ({len(combined) / float(sample_rate):.1f}s)")
        return combined, sample_rate


# Global pipeline instance
forge_pipeline = ForgePipeline()
