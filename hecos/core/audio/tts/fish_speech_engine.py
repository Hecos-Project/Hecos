"""
MODULE: Fish Speech TTS Engine
DESCRIPTION: High-level engine implementation for Fish Speech TTS.
             Orchestrates parameter resolution, client communication, chunked synthesis,
             and audio playback. Fully backward-compatible facade.
"""

import os
import re
import glob
import time
import tempfile
import threading
from typing import Optional, Tuple

from hecos.core.logging import logger
from hecos.core.audio.tts.base_engine import BaseTTSEngine
from hecos.core.audio.tts.fish_speech.params import FishSpeechParams, resolve_fish_params, get_project_root
from hecos.core.audio.tts.fish_speech.client import FishSpeechClient, is_ormsgpack_available
from hecos.core.audio.tts.fish_speech.audio import FishSpeechAudio


class FishSpeechEngine(BaseTTSEngine):
    """
    Fish Speech TTS Engine.
    Interacts with a local Fish Speech API server or Fish Audio Cloud API with
    zero-shot voice cloning capabilities.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._is_speaking = False
        self._stop_flag = False
        logger.debug("FISH_SPEECH", f"FishSpeechEngine initialized (ormsgpack available: {is_ormsgpack_available()})")

    # ── Availability & Readiness ─────────────────────────────────────────────

    @staticmethod
    def is_available() -> bool:
        """Returns True if the required libraries are installed."""
        return FishSpeechClient.is_available()

    @classmethod
    def model_ready(cls) -> bool:
        """Checks if the configured Fish Speech endpoint or local model is ready."""
        return FishSpeechClient.model_ready()

    def preload(self, delay: float = 2.0):
        """Preloads the local Fish Speech server in background if configured for local use."""
        try:
            from hecos.core.audio.tts.fish_speech_daemon import FishSpeechDaemon
            daemon = FishSpeechDaemon.get_instance()
            if daemon.is_local_target():
                daemon.preload(delay=delay)
        except Exception as e:
            logger.debug("FISH_SPEECH", f"Preload non-fatal notice: {e}")

    # ── Parameters & Chunk Synthesis ─────────────────────────────────────────

    # ── Parameters & Chunk Synthesis ─────────────────────────────────────────

    def _get_fish_params(self, kwargs: dict) -> FishSpeechParams:
        """Resolves parameters merging global config, presets, and session overrides."""
        return resolve_fish_params(kwargs)

    def _synthesize_chunk(self, text: str, p: FishSpeechParams) -> Optional[bytes]:
        """Sends a single synthesis request to Fish Speech API (with chunk-level cache check)."""
        vol = getattr(p, "volume", 1.0)
        cache = None
        try:
            from hecos.core.audio.tts_cache import TTSCache
            cache = TTSCache.get_instance()
            cached_bytes = cache.get_bytes(
                text=text,
                engine="fish_speech",
                voice=p.ref_audio or p.reference_id,
                session_overrides={"fish_temperature": p.temperature, "fish_top_p": p.top_p, "fish_chunk_length": p.chunk_length, "fish_volume": vol, "fish_norm": "v2"}
            )
            if cached_bytes:
                return cached_bytes
        except Exception as _c_err:
            logger.debug("FISH_SPEECH", f"Chunk cache lookup notice: {_c_err}")

        chunk_bytes = FishSpeechClient.synthesize_chunk(
            text=text,
            api_url=p.api_url,
            api_key=p.api_key,
            ref_audio=p.ref_audio,
            ref_text=p.ref_text,
            temp=p.temperature,
            top_p=p.top_p,
            rep_pen=p.repetition_penalty,
            max_tokens=p.max_new_tokens,
            chunk_length=p.chunk_length,
            seed=p.seed,
            normalize=p.normalize,
            use_memory_cache=p.use_memory_cache,
            reference_id=p.reference_id
        )

        if chunk_bytes:
            # Normalize and amplify audio chunk to match broadcast / Piper loudness levels
            chunk_bytes = FishSpeechAudio.normalize_wav_bytes(chunk_bytes, volume_factor=vol)

        if chunk_bytes and cache:
            try:
                cache.put_bytes(
                    text=text,
                    engine="fish_speech",
                    audio_bytes=chunk_bytes,
                    voice=p.ref_audio or p.reference_id,
                    session_overrides={"fish_temperature": p.temperature, "fish_top_p": p.top_p, "fish_chunk_length": p.chunk_length, "fish_volume": vol, "fish_norm": "v2"}
                )
            except Exception as _c_put_err:
                logger.debug("FISH_SPEECH", f"Chunk cache store notice: {_c_put_err}")

        return chunk_bytes

    # ── Core Interface Methods ───────────────────────────────────────────────

    def generate_wav(self, text: str, filepath: str, **kwargs) -> bool:
        if not text:
            logger.warning("FISH_SPEECH", "generate_wav called with empty text.")
            return False

        self._stop_flag = False
        logger.info("FISH_SPEECH", f"generate_wav starting for: '{text[:80]}...' -> {filepath}")
        p = self._get_fish_params(kwargs)
        # S2-Pro (local) and S2.1-Pro (cloud) natively support inline expressive tags [whisper], [laughing], etc.
        text = re.sub(r'\s+', ' ', text).strip()

        if self._stop_flag:
            logger.warning("FISH_SPEECH", "Synthesis halted early due to stop flag.")
            return False

        wav_bytes = self._synthesize_chunk(text=text, p=p)
        if self._stop_flag:
            logger.warning("FISH_SPEECH", "Synthesis halted early due to stop flag.")
            return False

        if not wav_bytes:
            logger.error("FISH_SPEECH", "generate_wav failed: no audio bytes returned.")
            return False

        try:
            os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
            with open(filepath, "wb") as f:
                f.write(wav_bytes)
            file_ok = os.path.exists(filepath) and os.path.getsize(filepath) > 0
            if file_ok:
                logger.info("FISH_SPEECH", f"✅ generate_wav successfully saved {os.path.getsize(filepath)} bytes to {filepath}")
            else:
                logger.error("FISH_SPEECH", f"generate_wav wrote empty file at {filepath}")
            return file_ok
        except Exception as e:
            logger.error("FISH_SPEECH", f"Failed to save generated WAV to {filepath}: {e}")
            return False

    def generate_wav_chunked(self, text: str, filepath: str, progress_callback=None, on_chunk_ready=None, **kwargs) -> bool:
        """
        Synthesizes text, optionally chunking by sentence for long answers, tracks progress,
        and invokes on_chunk_ready progressively as each chunk audio becomes available.
        """
        if not text:
            logger.warning("FISH_SPEECH", "generate_wav_chunked called with empty text.")
            return False

        self._stop_flag = False
        p = self._get_fish_params(kwargs)
        # S2-Pro (local) and S2.1-Pro (cloud) natively support inline expressive tags [whisper], [laughing], etc.
        text = re.sub(r'\s+', ' ', text).strip()
        if p.chunk_sentences:
            sentences = [s.strip() for s in re.split(r'(?<=[.!?。])\s+', text) if s.strip()]
        else:
            sentences = [text]

        if not sentences:
            logger.warning("FISH_SPEECH", "No valid sentences found after splitting.")
            return False

        # Propagate active emotion directives (e.g. [whisper], [laughing]) across chunks
        current_directive = ""
        propagated_sentences = []
        for s in sentences:
            m = re.match(r'^(\[[a-zA-Z\s_-]+\]\s*)+', s)
            if m:
                current_directive = m.group(0).strip()
            elif current_directive:
                s = f"{current_directive} {s}"
            propagated_sentences.append(s)
        sentences = propagated_sentences

        logger.info("FISH_SPEECH", f"generate_wav_chunked: {len(sentences)} sentence(s) to process (chunk_sentences={p.chunk_sentences})")
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)

        if len(sentences) == 1:
            if progress_callback:
                try:
                    progress_callback(0, 1)
                except TypeError:
                    progress_callback(0)
            ok = self.generate_wav(sentences[0], filepath, **kwargs)
            if ok and on_chunk_ready:
                try:
                    with open(filepath, "rb") as _f:
                        _cbytes = _f.read()
                    on_chunk_ready(0, 1, filepath, _cbytes)
                except Exception as _cb_err:
                    logger.debug("FISH_SPEECH", f"on_chunk_ready single callback notice: {_cb_err}")
            if progress_callback and ok:
                try:
                    progress_callback(1, 1)
                except TypeError:
                    progress_callback(100)
            return ok

        # Multi-sentence: synthesize each chunk and combine
        temp_files = []
        try:
            import copy
            for i, s in enumerate(sentences):
                if self._stop_flag:
                    logger.warning("FISH_SPEECH", "Synthesis halted early due to stop flag.")
                    return False

                logger.debug("FISH_SPEECH", f"Synthesizing chunk {i+1}/{len(sentences)}: '{s[:60]}...'")

                if progress_callback:
                    try:
                        progress_callback(i, len(sentences))
                    except TypeError:
                        progress_callback(int((i / len(sentences)) * 100))

                # Dynamic token limit based on sentence length to prevent runaway generation or timeouts
                chunk_max_tokens = min(max(len(s) * 4, 160), p.max_new_tokens or 512)
                chunk_p = p._replace(max_new_tokens=chunk_max_tokens)

                chunk_bytes = self._synthesize_chunk(text=s, p=chunk_p)
                if self._stop_flag:
                    logger.warning("FISH_SPEECH", "Synthesis halted early due to stop flag.")
                    return False

                if not chunk_bytes:
                    logger.warning("FISH_SPEECH", f"Chunk {i+1}/{len(sentences)} failed to synthesize, skipping.")
                    if i == 0 and not temp_files:
                        logger.error("FISH_SPEECH", "Aborting remaining chunks as endpoint appears offline.")
                        break
                    continue

                tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
                tmp.write(chunk_bytes)
                tmp.close()
                temp_files.append(tmp.name)

                if on_chunk_ready:
                    try:
                        on_chunk_ready(i, len(sentences), tmp.name, chunk_bytes)
                    except Exception as _cb_err:
                        logger.debug("FISH_SPEECH", f"on_chunk_ready callback notice: {_cb_err}")

            if self._stop_flag:
                logger.warning("FISH_SPEECH", "Synthesis halted early due to stop flag.")
                return False

            if not temp_files:
                logger.error("FISH_SPEECH", "generate_wav_chunked: zero chunks were successfully synthesized.")
                return False

            logger.info("FISH_SPEECH", f"Merging {len(temp_files)} audio chunk(s) into final WAV: {filepath}")
            self._merge_wav_files(temp_files, filepath, volume_factor=getattr(p, "volume", 1.0))

            if progress_callback:
                try:
                    progress_callback(len(sentences), len(sentences))
                except TypeError:
                    progress_callback(100)

            file_ok = os.path.exists(filepath) and os.path.getsize(filepath) > 0
            if file_ok:
                logger.info("FISH_SPEECH", f"✅ generate_wav_chunked finished: {filepath} ({os.path.getsize(filepath)} bytes)")
            return file_ok
        finally:
            for tmp_p in temp_files:
                try:
                    if os.path.exists(tmp_p):
                        os.remove(tmp_p)
                except Exception:
                    pass

    def _merge_wav_files(self, file_list: list, output_path: str, volume_factor: float = 1.0):
        """Merges multiple WAV files into a single WAV file with silence pause and volume normalization."""
        FishSpeechAudio.merge_wav_files(file_list, output_path, volume_factor=volume_factor)

    def speak(self, text: str, state=None, _run_id=None, _timeout=0, _start=0, **kwargs):
        """Synthesizes text and plays it progressively chunk-by-chunk on the speaker."""
        self._stop_flag = False
        self._is_speaking = True
        logger.info("FISH_SPEECH", f"speak() started (progressive mode) for text: '{text[:80]}...'")
        if state:
            state.system_speaking = True

        import queue
        import shutil
        chunk_queue = queue.Queue()
        playback_done = threading.Event()

        def _speaker_worker():
            while True:
                item = chunk_queue.get()
                if item is None:
                    break
                chunk_file = item
                try:
                    if not self._stop_flag and os.path.exists(chunk_file):
                        logger.debug("FISH_SPEECH", f"Progressive playback starting chunk: {chunk_file}")
                        FishSpeechAudio.play_wav(chunk_file, is_stopped_fn=lambda: self._stop_flag)
                except Exception as p_err:
                    logger.warning("FISH_SPEECH", f"Speaker worker error: {p_err}")
                finally:
                    try:
                        if os.path.exists(chunk_file):
                            os.remove(chunk_file)
                    except Exception:
                        pass
                    chunk_queue.task_done()
            playback_done.set()

        speaker_thread = threading.Thread(target=_speaker_worker, daemon=True, name="FishSpeechSpeakerWorker")
        speaker_thread.start()

        def _on_chunk_ready(idx, total, chunk_path, chunk_bytes):
            if self._stop_flag:
                return
            try:
                play_tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
                play_tmp.close()
                shutil.copyfile(chunk_path, play_tmp.name)
                chunk_queue.put(play_tmp.name)
                logger.debug("FISH_SPEECH", f"Enqueued chunk {idx+1}/{total} for progressive speaker playback.")
            except Exception as _q_err:
                logger.warning("FISH_SPEECH", f"Failed to enqueue chunk {idx+1}: {_q_err}")

        tmp_final = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_final = tmp.name

            success = self.generate_wav_chunked(text, tmp_final, on_chunk_ready=_on_chunk_ready, **kwargs)
            if not success or self._stop_flag:
                logger.warning("FISH_SPEECH", "speak() aborted: generation failed or stopped.")
        except Exception as e:
            logger.error("FISH_SPEECH", f"speak() error: {e}")
        finally:
            chunk_queue.put(None)
            speaker_thread.join(timeout=180)
            self._is_speaking = False
            if state:
                state.system_speaking = False
            if tmp_final and os.path.exists(tmp_final):
                try:
                    os.remove(tmp_final)
                except Exception:
                    pass

    def stop(self):
        """Halts synthesis and aborts local playback."""
        logger.info("FISH_SPEECH", "stop() invoked — halting synthesis and aborting playback.")
        self._stop_flag = True
        self._is_speaking = False
        FishSpeechAudio.stop_playback()

    def get_available_voices(self) -> dict:
        """
        Returns available voices for Fish Speech:
        - "default": Base Voice (Zero-Shot / Default Model Voice)
        - Personal WAV files discovered in assets/voice_clones.
        """
        voices = {"default": "Default Voice (Zero-Shot / Base)"}
        try:
            clones_dir = os.path.join(get_project_root(), "hecos", "assets", "voice_clones")
            if not os.path.exists(clones_dir):
                clones_dir = os.path.join(get_project_root(), "assets", "voice_clones")

            if os.path.exists(clones_dir):
                for wav in sorted(glob.glob(os.path.join(clones_dir, "*.wav"))):
                    bname = os.path.basename(wav)
                    name = os.path.splitext(bname)[0].strip()
                    voices[bname] = f"Clone: {name}"
            logger.debug("FISH_SPEECH", f"Discovered {len(voices)} voice option(s).")
        except Exception as e:
            logger.warning("FISH_SPEECH", f"Error scanning voice clones: {e}")

        return voices


# ── Singleton ─────────────────────────────────────────────────────────────────

_engine_instance: Optional[FishSpeechEngine] = None
_engine_lock = threading.Lock()


def get_engine() -> FishSpeechEngine:
    global _engine_instance
    if _engine_instance is None:
        with _engine_lock:
            if _engine_instance is None:
                _engine_instance = FishSpeechEngine()
    return _engine_instance
