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

    @staticmethod
    def model_ready() -> bool:
        """Returns True only if the XTTSv2 model files are already downloaded on disk."""
        try:
            import os
            from TTS.utils.manage import ModelManager
            manager = ModelManager()
            model_path, _, _ = manager.download_model("tts_models/multilingual/multi-dataset/xtts_v2")
            return os.path.exists(model_path)
        except Exception:
            # Fallback: check common HuggingFace/TTS cache paths
            import os
            home = os.path.expanduser("~")
            possible_paths = [
                os.path.join(home, ".local", "share", "tts", "tts_models--multilingual--multi-dataset--xtts_v2"),
                os.path.join(home, "AppData", "Local", "tts", "tts_models--multilingual--multi-dataset--xtts_v2"),
                os.path.join(home, "AppData", "Roaming", "tts", "tts_models--multilingual--multi-dataset--xtts_v2"),
            ]
            return any(os.path.isdir(p) and os.listdir(p) for p in possible_paths)

    # ── Lazy model loading ────────────────────────────────────────────────────

    def _ensure_model(self) -> bool:
        if self._tts is not None:
            return True
        with self._lock:
            if self._tts is not None:
                return True
            try:
                import os
                model_name = "tts_models/multilingual/multi-dataset/xtts_v2"

                # Auto-agree to Coqui TOS so it doesn't block on stdin
                os.environ["COQUI_TOS_AGREED"] = "1"

                # Apply compatibility patches for TTS 0.22.0 + transformers 5.x + PyTorch 2.6+
                # These are idempotent and safe to run on every load.
                try:
                    from hecos.core.audio.tts.patch_tts_compat import apply_all_patches
                    apply_all_patches()
                except Exception as patch_err:
                    logger.warning("XTTS", f"TTS compatibility patch failed (non-fatal): {patch_err}")

                from TTS.api import TTS


                is_ready = XttsEngine.model_ready()
                if not is_ready:
                    logger.info("XTTS", "⏳ XTTSv2 model not yet downloaded. Starting download (~1.8 GB). This may take several minutes...")
                else:
                    logger.info("XTTS", "Loading XTTSv2 model (cached)...")

                # --- GPU resolution ---
                try:
                    import torch
                    cuda_available = torch.cuda.is_available()
                except Exception:
                    cuda_available = False

                try:
                    from hecos.core.audio.device_manager import get_audio_config
                    cfg_gpu = get_audio_config().get("xtts", {}).get("gpu_acceleration", "auto")
                except Exception:
                    cfg_gpu = "auto"

                if cfg_gpu == "gpu":
                    if not cuda_available:
                        logger.warning("XTTS", "GPU forced but CUDA is not available. Check that PyTorch is installed with CUDA support (pip install torch --index-url https://download.pytorch.org/whl/cu128). Falling back to CPU.")
                        use_gpu = False
                    else:
                        use_gpu = True
                elif cfg_gpu == "cpu":
                    use_gpu = False
                else:  # auto
                    use_gpu = cuda_available
                    if not cuda_available:
                        logger.info("XTTS", "CUDA not detected — running on CPU. For faster synthesis install PyTorch with CUDA support.")

                self._tts = TTS(model_name, gpu=use_gpu)
                if use_gpu:
                    gpu_name = "unknown"
                    try:
                        gpu_name = torch.cuda.get_device_name(0)
                    except Exception:
                        pass
                    logger.info("XTTS", f"✅ XTTSv2 model loaded on GPU ({gpu_name}).")
                else:
                    logger.info("XTTS", "✅ XTTSv2 model loaded on CPU.")
                
                logger.info("XTTS", "All default XTTS voices are built-in and ready.")
                return True
            except Exception as e:
                logger.error("XTTS", f"Failed to load XTTSv2 model: {e}")
                return False

    def _get_xtts_params(self, kwargs: dict):
        """Resolve params from kwargs / audio config."""
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
        
        speed = kwargs.get("speed")
        if speed is None:
            speed = float(cfg.get("speed", 1.0))
        else:
            try:
                speed = float(speed)
            except Exception:
                speed = 1.0

        chunk_sentences = cfg.get("chunk_sentences", True)
        temperature = float(cfg.get("temperature", 0.75))
        repetition_penalty = float(cfg.get("repetition_penalty", 5.0))
        
        speaker_wav = cfg.get("speaker_wav", "").strip()
        import os
        if speaker_wav and os.path.exists(speaker_wav):
            # If cloning voice is active and valid, don't use default speaker name
            speaker = None
        else:
            speaker_wav = None

        return speaker, language, speed, chunk_sentences, speaker_wav, temperature, repetition_penalty

    # ── Core synthesis ────────────────────────────────────────────────────────

    def generate_wav(self, text: str, filepath: str, **kwargs) -> bool:
        if not text:
            return False
        if not self._ensure_model():
            return False

        speaker, language, speed, chunk_sentences, speaker_wav, temp, rep_pen = self._get_xtts_params(kwargs)
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            self._tts.tts_to_file(
                text=text,
                speaker=speaker,
                language=language,
                speed=speed,
                speaker_wav=speaker_wav,
                split_sentences=chunk_sentences,
                temperature=temp,
                repetition_penalty=rep_pen,
                file_path=filepath
            )
            return os.path.exists(filepath)
        except Exception as e:
            logger.error("XTTS", f"generate_wav error: {e}")
            return False

    def generate_wav_chunked(self, text: str, filepath: str, progress_callback=None, **kwargs) -> bool:
        """
        Generate WAV from text using XTTSv2.
        Manually chunks text and tracks progress, then concatenates audio to avoid UI hanging at 0%.
        """
        if not text:
            return False
        if not self._ensure_model():
            return False

        speaker, language, speed, chunk_sentences, speaker_wav, temp, rep_pen = self._get_xtts_params(kwargs)

        import re
        import numpy as np
        from scipy.io import wavfile
        
        # Clean up newlines which can cause hallucinations
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Chunk text if required
        if chunk_sentences:
            sentences = [s.strip() for s in re.split(r'(?<=[.!?。])\s+', text) if s.strip()]
        else:
            sentences = [text]
            
        if not sentences:
            return False

        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        audio_chunks = []
        try:
            for i, sentence in enumerate(sentences):
                # Update progress
                if progress_callback:
                    try:
                        progress_callback(i, len(sentences))
                    except TypeError:
                        progress_callback(int((i / len(sentences)) * 100))
                
                # Generate audio for the sentence
                wav = self._tts.tts(
                    text=sentence,
                    speaker=speaker,
                    language=language,
                    speed=speed,
                    speaker_wav=speaker_wav,
                    temperature=temp,
                    repetition_penalty=rep_pen,
                    split_sentences=False
                )
                
                # Convert to int16 numpy array if it's not already
                wav_arr = np.array(wav)
                if wav_arr.dtype != np.int16:
                    wav_arr = np.int16(wav_arr * 32767.0)
                
                audio_chunks.append(wav_arr)
            
            # Concatenate all audio arrays
            if not audio_chunks:
                return False
                
            final_audio = np.concatenate(audio_chunks)
            
            # Write to WAV file using the TTS config sample rate
            sample_rate = 24000
            try:
                sample_rate = self._tts.synthesizer.output_sample_rate
            except Exception:
                pass
                
            wavfile.write(filepath, sample_rate, final_audio)
            
            # Final 100% progress
            if progress_callback:
                try:
                    progress_callback(len(sentences), len(sentences))
                except TypeError:
                    progress_callback(100)
                    
            return os.path.exists(filepath)
        except Exception as e:
            logger.error("XTTS", f"Synthesis error: {e}")
            return False



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

        speaker, language, speed, chunk_sentences, speaker_wav, temp, rep_pen = self._get_xtts_params(kwargs)

        import re, tempfile, wave
        import numpy as np

        if chunk_sentences:
            sentences = [s.strip() for s in re.split(r'(?<=[.!?。])\s+', text) if s.strip()]
        else:
            sentences = [text]
            
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
                        speed=speed,
                        speaker_wav=speaker_wav,
                        split_sentences=chunk_sentences,
                        temperature=temp,
                        repetition_penalty=rep_pen,
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
