"""
MODULE: Kokoro TTS Engine
DESCRIPTION: Implementation for Kokoro using the `kokoro` PyTorch package.
             Lazy-loads a single KPipeline at a time; evicts the previous pipeline
             before loading a different language to avoid OOM errors.

             Requires:
               pip install kokoro misaki[en] soundfile

             Italian / Spanish / French / Japanese voices additionally require
             espeak-ng to be installed as a system binary:
               https://github.com/espeak-ng/espeak-ng/releases
"""

import gc
import math
import os
import shutil
import subprocess
import tempfile
import threading
import time

from hecos.core.logging import logger
from hecos.core.audio.tts.base_engine import BaseTTSEngine


def normalize_float32_audio(audio_f32, target_rms_db: float = -14.0, volume_factor: float = 1.0):
    """
    Normalizes float32 audio loudness to match broadcast / Piper / Fish-Speech levels (~ -14 to -16 dBFS RMS).
    Uses speech-active RMS detection (ignoring silence) and smooth soft-knee tanh compression
    for peaks to avoid clipping while maintaining maximum clarity and dynamic range.
    """
    if audio_f32 is None:
        return audio_f32
    import numpy as np
    if hasattr(audio_f32, "detach"):
        data = audio_f32.detach().cpu().numpy().astype(np.float32)
    else:
        data = np.asarray(audio_f32, dtype=np.float32)
    if data.size == 0:
        return data

    abs_data = np.abs(data)
    non_silent = data[abs_data > 0.01]
    if len(non_silent) == 0:
        non_silent = data

    current_rms = float(np.sqrt(np.mean(non_silent**2)))
    if current_rms <= 1e-6:
        return data

    effective_target_db = target_rms_db
    if volume_factor > 0 and volume_factor != 1.0:
        effective_target_db += 20.0 * math.log10(volume_factor)

    target_rms = 10.0 ** (effective_target_db / 20.0)
    gain = target_rms / current_rms
    gain = float(np.clip(gain, 0.5, 12.0))

    amplified = data * gain
    thresh = 0.70
    limit = 0.98
    headroom = limit - thresh

    signs = np.sign(amplified)
    abs_amp = np.abs(amplified)
    mask = abs_amp > thresh
    compressed = abs_amp.copy()
    if np.any(mask):
        excess = abs_amp[mask] - thresh
        compressed[mask] = thresh + headroom * np.tanh(excess / headroom)

    out = signs * compressed
    return np.clip(out, -1.0, 1.0).astype(np.float32)

try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False

try:
    import soundfile as sf
    SOUNDFILE_AVAILABLE = True
except ImportError:
    SOUNDFILE_AVAILABLE = False


# Ensure eSpeak NG (needed for non-English voices) is findable even if
# its install directory was not added to the system PATH at install time.
def _patch_espeak_path():
    import os
    espeak_dir = r"C:\Program Files\eSpeak NG"
    if os.path.isdir(espeak_dir) and espeak_dir not in os.environ.get("PATH", ""):
        os.environ["PATH"] = espeak_dir + os.pathsep + os.environ.get("PATH", "")

_patch_espeak_path()


# ── Voice registry ─────────────────────────────────────────────────────────────

# Known Kokoro voices (v1.0 model).  Key format: <lang_code><gender>_<name>
# lang_code: a=American EN, b=British EN, e=Spanish, f=French, h=Hindi,
#            i=Italian, p=Portuguese BR, j=Japanese, z=Mandarin
KOKORO_VOICES = {
    "af_heart":      "Heart (Female, US)",
    "af_alloy":      "Alloy (Female, US)",
    "af_bella":      "Bella (Female, US)",
    "af_jessica":    "Jessica (Female, US)",
    "af_nicole":     "Nicole (Female, US)",
    "af_sarah":      "Sarah (Female, US)",
    "af_sky":        "Sky (Female, US)",
    "am_adam":       "Adam (Male, US)",
    "am_echo":       "Echo (Male, US)",
    "am_eric":       "Eric (Male, US)",
    "am_fenrir":     "Fenrir (Male, US)",
    "am_liam":       "Liam (Male, US)",
    "am_michael":    "Michael (Male, US)",
    "am_onyx":       "Onyx (Male, US)",
    "am_puck":       "Puck (Male, US)",
    "bf_emma":       "Emma (Female, GB)",
    "bf_isabella":   "Isabella (Female, GB)",
    "bm_george":     "George (Male, GB)",
    "bm_lewis":      "Lewis (Male, GB)",
    "if_sara":       "Sara (Female, IT)",
    "im_nicola":     "Nicola (Male, IT)",
}

# Languages that ship phonemes via misaki (no espeak-ng needed)
_MISAKI_NATIVE_LANGS = {"a", "b"}  # American EN, British EN

# Friendly names for log messages
_LANG_NAMES = {
    "a": "American English", "b": "British English",
    "e": "Spanish",          "f": "French",
    "h": "Hindi",            "i": "Italian",
    "p": "Portuguese (BR)",  "j": "Japanese",
    "z": "Mandarin Chinese",
}


def _espeak_available() -> bool:
    """Return True if the espeak-ng binary is reachable on PATH."""
    return shutil.which("espeak-ng") is not None


class KokoroEngine(BaseTTSEngine):
    """
    Kokoro TTS engine.

    Memory policy: only ONE KPipeline lives in memory at a time.
    Switching to a different language evicts the previous pipeline,
    calls gc.collect() and (if available) torch.cuda.empty_cache()
    before allocating the new one.
    """

    def __init__(self):
        self._pipeline = None        # Active KPipeline instance
        self._pipeline_lang = None   # lang_code of the loaded pipeline
        self._lock = threading.Lock()
        self._is_speaking = False
        self._stop_flag = False

        if not _espeak_available():
            logger.warning(
                "KOKORO",
                "⚠️ eSpeak-NG non è installato o non è nel PATH! "
                "Le voci italiane (es. Nicola, Sara) e altre lingue non-inglesi NON funzioneranno. "
                "Per risolvere, installalo scaricando il .msi da: https://github.com/espeak-ng/espeak-ng/releases"
            )

    # ── Availability ──────────────────────────────────────────────────────────

    @staticmethod
    def is_available() -> bool:
        try:
            import kokoro  # noqa: F401
            return True
        except ImportError:
            return False

    def get_available_voices(self) -> dict:
        """Returns the full dictionary of all known Kokoro voices, appending a cloud icon if not cached."""
        result = {}
        try:
            from huggingface_hub import try_to_load_from_cache
            for k, v in KOKORO_VOICES.items():
                is_cached = try_to_load_from_cache("hexgrad/Kokoro-82M", f"voices/{k}.pt")
                # Also check local voices folder if user manually downloaded them there
                is_local = os.path.exists(f"voices/{k}.pt") or os.path.exists(os.path.join(os.path.dirname(__file__), "voices", f"{k}.pt"))
                
                if not is_cached and not is_local:
                    result[k] = f"{v} ☁️"
                else:
                    result[k] = v
        except Exception:
            result = KOKORO_VOICES.copy()

        # Merge local custom cloned voices (.pt)
        try:
            from .kokoro.voice_manager import KokoroVoiceManager
            result.update(KokoroVoiceManager.get_custom_voice_dict())
        except Exception as _cve:
            logger.debug("KOKORO", f"Notice checking custom Kokoro voices: {_cve}")

        return result

    # ── Memory management ─────────────────────────────────────────────────────

    def _evict_pipeline(self):
        """Unload the current pipeline and free memory."""
        if self._pipeline is not None:
            logger.info("KOKORO", f"Evicting pipeline for lang='{self._pipeline_lang}' to free RAM.")
            self._pipeline = None
            self._pipeline_lang = None
            gc.collect()
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except Exception:
                pass

    def _get_pipeline(self, lang_code: str):
        """
        Return the active KPipeline for *lang_code*, loading it if necessary.
        If a different language is currently loaded, it is evicted first.
        Returns None on failure (missing espeak-ng, import error, …).
        """
        # Fast path: already loaded
        if self._pipeline is not None and self._pipeline_lang == lang_code:
            return self._pipeline

        with self._lock:
            # Re-check under lock
            if self._pipeline is not None and self._pipeline_lang == lang_code:
                return self._pipeline

            # espeak-ng guard for non-native languages
            if lang_code not in _MISAKI_NATIVE_LANGS and not _espeak_available():
                lang_name = _LANG_NAMES.get(lang_code, lang_code)
                logger.error(
                    "KOKORO",
                    f"Voice language '{lang_name}' requires espeak-ng, which was not found. "
                    f"Install it from https://github.com/espeak-ng/espeak-ng/releases "
                    f"and add it to PATH, then restart Hecos."
                )
                return None

            # Evict old pipeline to avoid OOM
            if self._pipeline is not None:
                self._evict_pipeline()

            try:
                from kokoro import KPipeline
                from hecos.core.audio.device_manager import get_audio_config
                cfg = get_audio_config()
                model_path = cfg.get("kokoro", {}).get("model_path", "").strip()

                lang_name = _LANG_NAMES.get(lang_code, lang_code)
                logger.info("KOKORO", f"Loading Kokoro pipeline for '{lang_name}'…")
                if model_path:
                    logger.info("KOKORO", f"Using custom model path: {model_path}")
                    if os.path.isdir(model_path):
                        config_file = os.path.join(model_path, "config.json")
                        pth_file = os.path.join(model_path, "kokoro-v1_0.pth")
                        if not os.path.exists(pth_file):
                            import glob
                            pths = glob.glob(os.path.join(model_path, "*.pth"))
                            if pths:
                                pth_file = pths[0]
                        if os.path.exists(config_file) and os.path.exists(pth_file):
                            from kokoro.model import KModel
                            import torch
                            device = 'cuda' if torch.cuda.is_available() else 'cpu'
                            kmodel = KModel(config=config_file, model=pth_file).to(device).eval()
                            pipeline = KPipeline(lang_code=lang_code, model=kmodel)
                        else:
                            pipeline = KPipeline(lang_code=lang_code, repo_id=model_path)
                    elif os.path.isfile(model_path) and model_path.endswith(".pth"):
                        parent_dir = os.path.dirname(model_path)
                        config_file = os.path.join(parent_dir, "config.json")
                        if os.path.exists(config_file):
                            from kokoro.model import KModel
                            import torch
                            device = 'cuda' if torch.cuda.is_available() else 'cpu'
                            kmodel = KModel(config=config_file, model=model_path).to(device).eval()
                            pipeline = KPipeline(lang_code=lang_code, model=kmodel)
                        else:
                            pipeline = KPipeline(lang_code=lang_code, repo_id=model_path)
                    else:
                        pipeline = KPipeline(lang_code=lang_code, repo_id=model_path)
                else:
                    pipeline = KPipeline(lang_code=lang_code)
                self._pipeline = pipeline
                self._pipeline_lang = lang_code
                logger.info("KOKORO", f"Kokoro pipeline ready for '{lang_name}'.")
                return pipeline
            except Exception as e:
                logger.error("KOKORO", f"Failed to load Kokoro pipeline (lang='{lang_code}'): {e}")
                return None

    # ── Voice resolution ──────────────────────────────────────────────────────

    def _get_preset_dict(self, overrides: dict) -> dict:
        k_preset = overrides.get("kokoro_preset")
        if k_preset and k_preset != "default":
            try:
                from hecos.core.audio.device_manager import get_audio_config
                cfg = get_audio_config()
                return cfg.get("kokoro_presets", {}).get(k_preset) or {}
            except Exception:
                pass
        return {}

    def _get_voice(self, kwargs: dict) -> str:
        """Resolve voice ID from kwargs or global audio config."""
        # 1. Direct kwarg
        voice = kwargs.get("tts_voice") or kwargs.get("voice") or kwargs.get("kokoro_voice")
        # 2. session_overrides dict (passed by TTSManager from quick panel / chat)
        if not voice or voice == "default":
            overrides = kwargs.get("session_overrides") or {}
            p_dict = self._get_preset_dict(overrides)
            voice = overrides.get("kokoro_voice") or overrides.get("tts_voice") or p_dict.get("voice")
        # 3. Global audio config fallback
        if not voice or voice == "default":
            try:
                from hecos.core.audio.device_manager import get_audio_config
                cfg = get_audio_config()
                voice = cfg.get("kokoro", {}).get("voice", "af_heart")
            except Exception:
                voice = "af_heart"

        # Check against standard and custom voices
        custom_dict = {}
        try:
            from .kokoro.voice_manager import KokoroVoiceManager
            custom_dict = KokoroVoiceManager.get_custom_voice_dict()
        except Exception:
            pass

        if voice in KOKORO_VOICES or voice in custom_dict or (voice and (voice.endswith(".pt") or os.path.isabs(voice))):
            resolved = voice
        else:
            resolved = "af_heart"

        logger.info("KOKORO", f"Voice resolved: '{resolved}' (requested: '{voice}')")
        return resolved

    def _resolve_voice_and_lang(self, voice_id: str):
        """Resolves voice identifier to (voice_pack_or_name, lang_code)."""
        try:
            from .kokoro.voice_manager import KokoroVoiceManager
            pack, lang = KokoroVoiceManager.resolve_voice_pack(voice_id)
            if pack is not None:
                return pack, lang or "i"
        except Exception as _rve:
            logger.debug("KOKORO", f"Voice pack resolution notice: {_rve}")

        lang_code = voice_id[0] if (voice_id and len(voice_id) > 0 and voice_id[0] in "abefhijpz") else "a"
        return voice_id, lang_code

    def _get_speed(self, kwargs: dict) -> float:
        """Resolve speech speed from kwargs or global audio config."""
        speed = kwargs.get("speed") or kwargs.get("kokoro_speed")
        if not speed:
            overrides = kwargs.get("session_overrides") or {}
            speed = overrides.get("speed") or overrides.get("kokoro_speed") or self._get_preset_dict(overrides).get("speed")
        if speed:
            try:
                return float(speed)
            except (TypeError, ValueError):
                pass
        try:
            from hecos.core.audio.device_manager import get_audio_config
            cfg = get_audio_config()
            return float(cfg.get("kokoro", {}).get("speed", 1.0))
        except Exception:
            return 1.0

    def _get_alpha(self, kwargs: dict) -> float:
        """Resolve style / timbre weight (alpha) from kwargs or audio config."""
        import numpy as np
        alpha = kwargs.get("alpha") or kwargs.get("kokoro_alpha")
        if alpha is None:
            overrides = kwargs.get("session_overrides") or {}
            alpha = overrides.get("alpha") or overrides.get("kokoro_alpha") or self._get_preset_dict(overrides).get("alpha")
        if alpha is None:
            try:
                from hecos.core.audio.device_manager import get_audio_config
                cfg = get_audio_config()
                alpha = cfg.get("kokoro", {}).get("alpha", 1.0)
            except Exception:
                alpha = 1.0
        try:
            return float(np.clip(float(alpha), 0.0, 2.0))
        except (TypeError, ValueError):
            return 1.0

    def _get_beta(self, kwargs: dict) -> float:
        """Resolve prosody / cadence weight (beta) from kwargs or audio config."""
        import numpy as np
        beta = kwargs.get("beta") or kwargs.get("kokoro_beta")
        if beta is None:
            overrides = kwargs.get("session_overrides") or {}
            beta = overrides.get("beta") or overrides.get("kokoro_beta") or self._get_preset_dict(overrides).get("beta")
        if beta is None:
            try:
                from hecos.core.audio.device_manager import get_audio_config
                cfg = get_audio_config()
                beta = cfg.get("kokoro", {}).get("beta", 1.0)
            except Exception:
                beta = 1.0
        try:
            return float(np.clip(float(beta), 0.0, 2.0))
        except (TypeError, ValueError):
            return 1.0

    def _get_blend_voice(self, kwargs: dict) -> str:
        """Resolve secondary blend voice from kwargs or audio config."""
        blend = kwargs.get("blend_voice") or kwargs.get("kokoro_blend_voice")
        if blend is None:
            overrides = kwargs.get("session_overrides") or {}
            blend = overrides.get("blend_voice") or overrides.get("kokoro_blend_voice") or self._get_preset_dict(overrides).get("blend_voice")
        if blend is None:
            try:
                from hecos.core.audio.device_manager import get_audio_config
                cfg = get_audio_config()
                blend = cfg.get("kokoro", {}).get("blend_voice", "")
            except Exception:
                blend = ""
        return str(blend).strip() if blend else ""

    def _get_lang_code(self, kwargs: dict, voice_id: str) -> str:
        """Resolve G2P pipeline language code ('auto' or specific 'i','a','b','e','f','j','z','p','h')."""
        lang = kwargs.get("lang_code") or kwargs.get("kokoro_lang")
        if not lang:
            overrides = kwargs.get("session_overrides") or {}
            lang = overrides.get("lang_code") or overrides.get("kokoro_lang")
        if not lang:
            try:
                from hecos.core.audio.device_manager import get_audio_config
                cfg = get_audio_config()
                lang = cfg.get("kokoro", {}).get("lang_code", "auto")
            except Exception:
                lang = "auto"
        lang = str(lang).strip().lower()
        if lang and lang != "auto" and lang in "abefhijpz":
            return lang

        # Auto fallback based on voice ID prefix or custom voice metadata
        try:
            from .kokoro.voice_manager import KokoroVoiceManager
            _, detected = KokoroVoiceManager.resolve_voice_pack(voice_id)
            if detected:
                return detected
        except Exception:
            pass
        return voice_id[0] if (voice_id and len(voice_id) > 0 and voice_id[0] in "abefhijpz") else "a"

    def _resolve_voice_tensor(self, pipeline, voice_id: str, blend_voice: str = "", alpha: float = 1.0, beta: float = 1.0):
        """
        Loads primary voice and blends with optional secondary voice or scales style dynamics.
        Returns a torch.FloatTensor or the voice string identifier.
        """
        import torch
        import numpy as np

        def _load_one(vid):
            if not vid:
                return None
            if isinstance(vid, torch.Tensor):
                return vid
            try:
                from .kokoro.voice_manager import KokoroVoiceManager
                p, _ = KokoroVoiceManager.resolve_voice_pack(vid)
                if p is not None:
                    return p
            except Exception:
                pass
            if pipeline is not None:
                try:
                    return pipeline.load_voice(vid)
                except Exception as err:
                    logger.warning("KOKORO", f"Could not load voice '{vid}': {err}")
            return None

        pack1 = _load_one(voice_id)
        if pack1 is None:
            logger.warning("KOKORO", f"Falling back to default af_heart voice tensor.")
            pack1 = _load_one("af_heart")
            if pack1 is None:
                return voice_id

        if not isinstance(pack1, torch.Tensor):
            return voice_id

        if pack1.ndim == 2:
            pack1 = pack1.unsqueeze(1)

        # Check if secondary voice blending is requested
        if blend_voice and blend_voice.strip() and blend_voice.strip() != voice_id:
            pack2 = _load_one(blend_voice.strip())
            if pack2 is not None and isinstance(pack2, torch.Tensor):
                if pack2.ndim == 2:
                    pack2 = pack2.unsqueeze(1)
                
                # Alpha (timbre) and Beta (prosody) interpolation
                a = float(np.clip(alpha, 0.0, 1.0))
                b = float(np.clip(beta, 0.0, 1.0))
                p1 = pack1.to(dtype=torch.float32, device="cpu")
                p2 = pack2.to(dtype=torch.float32, device="cpu")
                blended = torch.zeros_like(p1)
                blended[:, :, :128] = a * p1[:, :, :128] + (1.0 - a) * p2[:, :, :128]
                blended[:, :, 128:] = b * p1[:, :, 128:] + (1.0 - b) * p2[:, :, 128:]
                return blended

        # Single voice mode: check if alpha/beta dynamic scaling is applied
        if (alpha != 1.0 or beta != 1.0) and isinstance(pack1, torch.Tensor):
            scaled = pack1.clone().to(dtype=torch.float32, device="cpu")
            if alpha != 1.0:
                scaled[:, :, :128] = scaled[:, :, :128] * float(alpha)
            if beta != 1.0:
                scaled[:, :, 128:] = scaled[:, :, 128:] * float(beta)
            return scaled

        return pack1

    def _get_volume(self, kwargs: dict) -> float:
        """Resolve output volume factor from kwargs, session_overrides or audio config."""
        import numpy as np
        vol = kwargs.get("volume") or kwargs.get("kokoro_volume")
        if vol is None:
            overrides = kwargs.get("session_overrides") or {}
            vol = overrides.get("volume") or overrides.get("kokoro_volume") or self._get_preset_dict(overrides).get("volume")
        if vol is None:
            try:
                from hecos.core.audio.device_manager import get_audio_config
                cfg = get_audio_config()
                vol = cfg.get("kokoro", {}).get("volume", 1.0)
            except Exception:
                vol = 1.0
        try:
            return float(np.clip(float(vol), 0.1, 3.0))
        except (TypeError, ValueError):
            return 1.0

    def _get_normalize(self, kwargs: dict) -> bool:
        """Resolve loudness normalization flag from kwargs, session_overrides or audio config."""
        norm = kwargs.get("normalize")
        if norm is None:
            norm = kwargs.get("kokoro_normalize")
        if norm is None:
            overrides = kwargs.get("session_overrides") or {}
            p_norm = self._get_preset_dict(overrides).get("normalize")
            norm = overrides.get("normalize") if overrides.get("normalize") is not None else overrides.get("kokoro_normalize")
            if norm is None:
                norm = p_norm
        if norm is None:
            try:
                from hecos.core.audio.device_manager import get_audio_config
                cfg = get_audio_config()
                norm = cfg.get("kokoro", {}).get("normalize", True)
            except Exception:
                norm = True
        return bool(norm)

    # ── Core synthesis ────────────────────────────────────────────────────────

    def generate_wav(self, text: str, filepath: str, **kwargs) -> bool:
        if not text:
            return False

        voice = self._get_voice(kwargs)
        blend_voice = self._get_blend_voice(kwargs)
        alpha = self._get_alpha(kwargs)
        beta = self._get_beta(kwargs)
        speed = self._get_speed(kwargs)
        volume = self._get_volume(kwargs)
        normalize = self._get_normalize(kwargs)
        lang_code = self._get_lang_code(kwargs, voice)
        lang_name = _LANG_NAMES.get(lang_code, lang_code)

        logger.info(
            "KOKORO",
            f"generate_wav: voice='{voice}', blend='{blend_voice}', alpha={alpha}, beta={beta}, "
            f"lang='{lang_name}' ({lang_code}), speed={speed}, volume={volume}, norm={normalize}"
        )

        # Italian (and other non-native langs) require espeak-ng
        if lang_code not in _MISAKI_NATIVE_LANGS and not _espeak_available():
            logger.error(
                "KOKORO",
                f"Voice '{voice}' ({lang_name}) requires espeak-ng, which was NOT found on PATH. "
                f"Download it from https://github.com/espeak-ng/espeak-ng/releases , "
                f"install it and make sure it is in the system PATH, then restart Hecos."
            )
            return False

        pipeline = self._get_pipeline(lang_code)

        if not pipeline:
            return False

        voice_target = self._resolve_voice_tensor(pipeline, voice, blend_voice, alpha, beta)

        try:
            import numpy as np
            os.makedirs(os.path.dirname(filepath), exist_ok=True)

            sentence_silence = kwargs.get("sentence_silence") or kwargs.get("kokoro_silence")
            if sentence_silence is None:
                overrides = kwargs.get("session_overrides") or {}
                sentence_silence = overrides.get("sentence_silence") or overrides.get("kokoro_silence") or self._get_preset_dict(overrides).get("sentence_silence")
            if sentence_silence is None:
                try:
                    from hecos.core.audio.device_manager import get_audio_config
                    sentence_silence = float(get_audio_config().get("kokoro", {}).get("sentence_silence", 0.0))
                except Exception:
                    sentence_silence = 0.0

            silence_samples = int(sentence_silence * 24000)
            silence_chunk = np.zeros(silence_samples, dtype=np.float32) if silence_samples > 0 else None

            chunks = []
            for _, _, audio in pipeline(text, voice=voice_target, speed=speed, split_pattern=r"\n+"):
                if audio is not None:
                    if hasattr(audio, "detach"):
                        arr = audio.detach().cpu().numpy().astype(np.float32)
                    else:
                        arr = np.asarray(audio, dtype=np.float32)

                    if normalize:
                        arr = normalize_float32_audio(arr, target_rms_db=-14.0, volume_factor=volume)
                    elif volume != 1.0:
                        arr = np.clip(arr * volume, -1.0, 1.0).astype(np.float32)

                    chunks.append(arr)
                    if silence_chunk is not None:
                        chunks.append(silence_chunk)
                        
            # Remove the last silence chunk if added
            if chunks and silence_chunk is not None and chunks[-1] is silence_chunk:
                chunks.pop()

            if not chunks:
                logger.warning("KOKORO", "generate_wav produced no audio chunks.")
                return False

            combined = np.concatenate(chunks)

            if SOUNDFILE_AVAILABLE:
                sf.write(filepath, combined, 24000)
            else:
                import struct
                import wave
                pcm16 = (combined * 32767).astype("int16")
                with wave.open(filepath, "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(24000)
                    wf.writeframes(struct.pack(f"<{len(pcm16)}h", *pcm16))

            return os.path.exists(filepath)
        except Exception as e:
            logger.error("KOKORO", f"generate_wav error: {e}")
            return False

    def generate_wav_chunked(self, text: str, filepath: str, progress_callback=None, **kwargs) -> bool:
        # Kokoro handles chunking internally via split_pattern
        return self.generate_wav(text, filepath, **kwargs)

    def speak(self, text: str, state=None, _run_id=None, _timeout=0, _start=0, session_overrides=None, **kwargs):
        if not text:
            return

        if session_overrides:
            kwargs["session_overrides"] = session_overrides
        voice = self._get_voice(kwargs)
        blend_voice = self._get_blend_voice(kwargs)
        alpha = self._get_alpha(kwargs)
        beta = self._get_beta(kwargs)
        speed = self._get_speed(kwargs)
        volume = self._get_volume(kwargs)
        normalize = self._get_normalize(kwargs)
        lang_code = self._get_lang_code(kwargs, voice)
        lang_name = _LANG_NAMES.get(lang_code, lang_code)

        logger.info(
            "KOKORO",
            f"speak: voice='{voice}', blend='{blend_voice}', alpha={alpha}, beta={beta}, "
            f"lang='{lang_name}' ({lang_code}), speed={speed}, volume={volume}, norm={normalize}"
        )

        if lang_code not in _MISAKI_NATIVE_LANGS and not _espeak_available():
            logger.error(
                "KOKORO",
                f"Voice '{voice}' ({lang_name}) requires espeak-ng, which was NOT found on PATH. "
                f"Install it from https://github.com/espeak-ng/espeak-ng/releases and restart Hecos."
            )
            return

        pipeline = self._get_pipeline(lang_code)

        if not pipeline:
            logger.warning("KOKORO", "Pipeline unavailable; skipping speak().")
            return

        voice_target = self._resolve_voice_tensor(pipeline, voice, blend_voice, alpha, beta)

        self._stop_flag = False
        self._is_speaking = True
        if state:
            state.system_speaking = True

        try:
            import numpy as np

            for _, _, audio in pipeline(text, voice=voice_target, speed=speed, split_pattern=r"[.!?。]\s*"):
                if self._stop_flag:
                    break
                if audio is None:
                    continue

                if hasattr(audio, "detach"):
                    arr = audio.detach().cpu().numpy().astype(np.float32)
                else:
                    arr = np.asarray(audio, dtype=np.float32)

                if normalize:
                    arr = normalize_float32_audio(arr, target_rms_db=-14.0, volume_factor=volume)
                elif volume != 1.0:
                    arr = np.clip(arr * volume, -1.0, 1.0).astype(np.float32)

                if SOUNDDEVICE_AVAILABLE:
                    sd.play(arr, samplerate=24000)
                    duration = len(arr) / 24000
                    end_time = time.time() + duration
                    while time.time() < end_time:
                        if self._stop_flag:
                            sd.stop()
                            break
                        time.sleep(0.05)
                else:
                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                        tmp_path = tmp.name
                    if SOUNDFILE_AVAILABLE:
                        sf.write(tmp_path, arr, 24000)
                    try:
                        import winsound
                        winsound.PlaySound(tmp_path, winsound.SND_FILENAME)
                    except Exception:
                        pass
                    finally:
                        try:
                            os.remove(tmp_path)
                        except Exception:
                            pass

        except Exception as e:
            logger.error("KOKORO", f"speak() error: {e}")
        finally:
            self._is_speaking = False
            if state:
                state.system_speaking = False

    def stop(self):
        logger.debug("KOKORO", "Stopping TTS.")
        self._stop_flag = True
        self._is_speaking = False
        if SOUNDDEVICE_AVAILABLE:
            try:
                sd.stop()
            except Exception:
                pass





# ── Singleton ─────────────────────────────────────────────────────────────────

_engine_instance: KokoroEngine | None = None
_engine_lock = threading.Lock()


def get_engine() -> KokoroEngine:
    global _engine_instance
    if _engine_instance is None:
        with _engine_lock:
            if _engine_instance is None:
                _engine_instance = KokoroEngine()
    return _engine_instance
