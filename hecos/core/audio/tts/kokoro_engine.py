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
import os
import shutil
import subprocess
import tempfile
import threading
import time

from hecos.core.logging import logger
from hecos.core.audio.tts.base_engine import BaseTTSEngine

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
        try:
            from huggingface_hub import try_to_load_from_cache
            import os
            result = {}
            for k, v in KOKORO_VOICES.items():
                is_cached = try_to_load_from_cache("hexgrad/Kokoro-82M", f"voices/{k}.pt")
                # Also check local voices folder if user manually downloaded them there
                is_local = os.path.exists(f"voices/{k}.pt") or os.path.exists(os.path.join(os.path.dirname(__file__), "voices", f"{k}.pt"))
                
                if not is_cached and not is_local:
                    result[k] = f"{v} ☁️"
                else:
                    result[k] = v
            return result
        except ImportError:
            return KOKORO_VOICES.copy()

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
                lang_name = _LANG_NAMES.get(lang_code, lang_code)
                logger.info("KOKORO", f"Loading Kokoro pipeline for '{lang_name}'…")
                pipeline = KPipeline(lang_code=lang_code)
                self._pipeline = pipeline
                self._pipeline_lang = lang_code
                logger.info("KOKORO", f"Kokoro pipeline ready for '{lang_name}'.")
                return pipeline
            except Exception as e:
                logger.error("KOKORO", f"Failed to load Kokoro pipeline (lang='{lang_code}'): {e}")
                return None

    # ── Voice resolution ──────────────────────────────────────────────────────

    def _get_voice(self, kwargs: dict) -> str:
        """Resolve voice ID from kwargs or global audio config."""
        voice = kwargs.get("tts_voice") or kwargs.get("voice")
        if not voice or voice == "default":
            try:
                from hecos.core.audio.device_manager import get_audio_config
                cfg = get_audio_config()
                voice = cfg.get("kokoro", {}).get("voice", "af_heart")
            except Exception:
                voice = "af_heart"
        return voice if voice in KOKORO_VOICES else "af_heart"

    def _get_speed(self, kwargs: dict) -> float:
        """Resolve speech speed from kwargs or global audio config."""
        speed = kwargs.get("speed")
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

    # ── Core synthesis ────────────────────────────────────────────────────────

    def generate_wav(self, text: str, filepath: str, **kwargs) -> bool:
        if not text:
            return False

        voice = self._get_voice(kwargs)
        speed = self._get_speed(kwargs)
        lang_code = voice[0] if voice else "a"
        pipeline = self._get_pipeline(lang_code)

        if not pipeline:
            return False

        try:
            import numpy as np
            os.makedirs(os.path.dirname(filepath), exist_ok=True)

            chunks = []
            for _, _, audio in pipeline(text, voice=voice, speed=speed, split_pattern=r"\n+"):
                if audio is not None:
                    chunks.append(audio)

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

    def speak(self, text: str, state=None, _run_id=None, _timeout=0, _start=0, **kwargs):
        if not text:
            return

        voice = self._get_voice(kwargs)
        speed = self._get_speed(kwargs)
        lang_code = voice[0] if voice else "a"
        pipeline = self._get_pipeline(lang_code)

        if not pipeline:
            logger.warning("KOKORO", "Pipeline unavailable; skipping speak().")
            return

        self._stop_flag = False
        self._is_speaking = True
        if state:
            state.system_speaking = True

        try:
            import numpy as np

            for _, _, audio in pipeline(text, voice=voice, speed=speed, split_pattern=r"[.!?。]\s*"):
                if self._stop_flag:
                    break
                if audio is None:
                    continue

                if SOUNDDEVICE_AVAILABLE:
                    sd.play(audio, samplerate=24000)
                    duration = len(audio) / 24000
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
                        sf.write(tmp_path, audio, 24000)
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
