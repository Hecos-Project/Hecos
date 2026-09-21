"""
MODULE: XTTSv2 TTS Engine
DESCRIPTION: Implementation for Coqui XTTSv2 using the TTS library.
             Lazy-loads the model on first use. Requires: pip install TTS
             WARNING: Heavy model (~1.8 GB download). Requires PyTorch.
             Best with a dedicated GPU; CPU is very slow.
"""

import os
import time
import threading

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


XTTS_DEFAULT_SPEAKER = "Claribel Dervla"

# Known built-in XTTS speakers (subset of the full list)
XTTS_BUILTIN_SPEAKERS = [
    "Claribel Dervla", "Daisy Studious", "Gracie Wise", "Tammie Ema",
    "Alison Dietlinde", "Ana Florence", "Annmarie Nele", "Asya Anara",
    "Brenda Stern", "Gitta Nikolina", "Henriette Usha", "Sofia Hellen",
    "Tammy Grit", "Tanja Adelina", "Vjollca Johnnie", "Andrew Chipper",
    "Badr Odhiambo", "Dionisio Schuyler", "Royston Min", "Viktor Eka",
    "Abrahan Mack", "Adde Michal", "Baldur Sanjin", "Craig Gutsy",
    "Damien Black", "Gilberto Mathias", "Ilkin Urbano", "Kazuhiko Atallah",
    "Ludvig Milivoj", "Suad Qasim", "Torcull Diarmuid", "Viktor Menelaos",
    "Zacharie Aimilios", "Nova Hogarth", "Maja Ruoho", "Uta Obando",
    "Lidiya Szekeres", "Chandra MacFarland", "Szofi Granger", "Camilla Holmström",
    "Louis Marchal", "Molly Kling", "Colette Olivier", "Filippo Fabrizi",
    "Jozef Owens", "Khalid Hassan", "Mikolaj Lisewski", "Weihong Gordan",
    "Wulfric Alan", "Narelle Moon"
]


def _get_project_root():
    current_file = os.path.abspath(__file__)
    return os.path.normpath(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_file))))
    )


class XttsEngine(BaseTTSEngine):
    """
    XTTSv2 engine. Wraps the Coqui TTS library with lazy model loading.
    Falls back gracefully if the library is not installed.
    """

    def __init__(self):
        self._tts = None      # Lazy-loaded TTS instance
        self._lock = threading.Lock()
        self._is_speaking = False
        self._stop_flag = False

    # ── Availability ──────────────────────────────────────────────────────────

    @staticmethod
    def is_available() -> bool:
        try:
            from TTS.api import TTS  # noqa: F401
            return True
        except ImportError:
            return False

    # ── Lazy model loading ────────────────────────────────────────────────────

    def _ensure_model(self) -> bool:
        if self._tts is not None:
            return True
        with self._lock:
            if self._tts is not None:
                return True
            try:
                from TTS.api import TTS
                logger.info("XTTS", "Loading XTTSv2 model (first use — may take a while)…")
                # gpu=True if available, falls back to CPU automatically
                try:
                    import torch
                    use_gpu = torch.cuda.is_available()
                except ImportError:
                    use_gpu = False
                self._tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=use_gpu)
                logger.info("XTTS", f"XTTSv2 model loaded ({'GPU' if use_gpu else 'CPU'}).")
                return True
            except Exception as e:
                logger.error("XTTS", f"Failed to load XTTSv2 model: {e}")
                return False

    def _get_voice_and_lang(self, kwargs: dict):
        """Resolve speaker name and language from kwargs / audio config."""
        try:
            from hecos.core.audio.device_manager import get_audio_config
            cfg = get_audio_config().get("xtts", {})
        except Exception:
            cfg = {}

        speaker = (
            kwargs.get("tts_voice")
            or kwargs.get("voice")
            or cfg.get("speaker", XTTS_DEFAULT_SPEAKER)
        )
        if speaker == "default" or not speaker:
            speaker = XTTS_DEFAULT_SPEAKER

        language = cfg.get("language", "it")
        return speaker, language

    # ── Core synthesis ────────────────────────────────────────────────────────

    def generate_wav(self, text: str, filepath: str, **kwargs) -> bool:
        if not text:
            return False
        if not self._ensure_model():
            return False

        speaker, language = self._get_voice_and_lang(kwargs)
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            self._tts.tts_to_file(
                text=text,
                speaker=speaker,
                language=language,
                file_path=filepath
            )
            return os.path.exists(filepath)
        except Exception as e:
            logger.error("XTTS", f"generate_wav error: {e}")
            return False

    def generate_wav_chunked(self, text: str, filepath: str, progress_callback=None, **kwargs) -> bool:
        """
        XTTS is slow; split by sentence and merge for long texts.
        """
        if not text:
            return False
        if not self._ensure_model():
            return False

        import re, wave, struct, tempfile
        import numpy as np

        speaker, language = self._get_voice_and_lang(kwargs)
        sentences = [s.strip() for s in re.split(r'(?<=[.!?。])\s+', text) if s.strip()]
        if not sentences:
            sentences = [text]

        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        tmp_files = []

        try:
            for i, sentence in enumerate(sentences):
                tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
                tmp.close()
                try:
                    self._tts.tts_to_file(
                        text=sentence,
                        speaker=speaker,
                        language=language,
                        file_path=tmp.name
                    )
                    tmp_files.append(tmp.name)
                    if progress_callback:
                        progress_callback(int((i + 1) / len(sentences) * 100))
                except Exception as e:
                    logger.warning("XTTS", f"Chunk {i} synthesis error: {e}")

            if not tmp_files:
                return False

            # Merge all chunks
            frames_all = []
            params = None
            for f in tmp_files:
                try:
                    with wave.open(f, 'rb') as wf:
                        if params is None:
                            params = wf.getparams()
                        frames_all.append(wf.readframes(wf.getnframes()))
                except Exception as e:
                    logger.warning("XTTS", f"Merge read error: {e}")

            if frames_all and params:
                with wave.open(filepath, 'wb') as out:
                    out.setparams(params)
                    for f in frames_all:
                        out.writeframes(f)

            return os.path.exists(filepath)
        finally:
            for f in tmp_files:
                try:
                    os.remove(f)
                except Exception:
                    pass

    def speak(self, text: str, state=None, _run_id=None, _timeout=0, _start=0, **kwargs):
        if not text:
            return
        if not self._ensure_model():
            logger.warning("XTTS", "Model unavailable; skipping speak().")
            return

        self._stop_flag = False
        self._is_speaking = True
        if state:
            state.system_speaking = True

        speaker, language = self._get_voice_and_lang(kwargs)

        import re, tempfile, wave
        import numpy as np

        sentences = [s.strip() for s in re.split(r'(?<=[.!?。])\s+', text) if s.strip()]
        if not sentences:
            sentences = [text]

        try:
            for sentence in sentences:
                if self._stop_flag:
                    break

                tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
                tmp.close()

                try:
                    self._tts.tts_to_file(
                        text=sentence,
                        speaker=speaker,
                        language=language,
                        file_path=tmp.name
                    )

                    if self._stop_flag:
                        break

                    if SOUNDDEVICE_AVAILABLE and os.path.exists(tmp.name) and os.path.getsize(tmp.name) > 44:
                        with wave.open(tmp.name, 'rb') as wf:
                            frames = wf.readframes(wf.getnframes())
                            rate = wf.getframerate()
                        pcm = np.frombuffer(frames, dtype="int16").astype("float32") / 32768.0
                        sd.play(pcm, samplerate=rate)
                        duration = len(pcm) / rate
                        end_time = time.time() + duration
                        while time.time() < end_time:
                            if self._stop_flag:
                                sd.stop()
                                break
                            time.sleep(0.05)
                    else:
                        try:
                            import winsound
                            winsound.PlaySound(tmp.name, winsound.SND_FILENAME)
                        except Exception:
                            pass
                except Exception as e:
                    logger.error("XTTS", f"speak sentence error: {e}")
                finally:
                    try:
                        os.remove(tmp.name)
                    except Exception:
                        pass

        except Exception as e:
            logger.error("XTTS", f"speak() outer error: {e}")
        finally:
            self._is_speaking = False
            if state:
                state.system_speaking = False

    def stop(self):
        logger.debug("XTTS", "Stopping TTS.")
        self._stop_flag = True
        self._is_speaking = False
        if SOUNDDEVICE_AVAILABLE:
            try:
                sd.stop()
            except Exception:
                pass

    def get_available_voices(self) -> dict:
        """
        Returns the built-in speaker list. If the model is loaded, query it directly.
        """
        if self._tts is not None:
            try:
                speakers = self._tts.speakers or XTTS_BUILTIN_SPEAKERS
                return {s: s for s in speakers}
            except Exception:
                pass
        return {s: s for s in XTTS_BUILTIN_SPEAKERS}


# ── Singleton ─────────────────────────────────────────────────────────────────

_engine_instance: XttsEngine | None = None
_engine_lock = threading.Lock()


def get_engine() -> XttsEngine:
    global _engine_instance
    if _engine_instance is None:
        with _engine_lock:
            if _engine_instance is None:
                _engine_instance = XttsEngine()
    return _engine_instance
