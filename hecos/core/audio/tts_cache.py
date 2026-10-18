"""
MODULE: TTS Cache
DESCRIPTION: High-performance persistent disk and memory cache for synthesized TTS audio.
             Accelerates repeated phrases, testing loops, and voice tests by returning
             pre-generated audio in <1ms instead of waiting for full neural model inference.
"""

import os
import glob
import json
import time
import shutil
import hashlib
import tempfile
import threading
from typing import Optional, Union, Dict, Any

from hecos.core.logging import logger
from hecos.core.constants import AUDIO_DIR


class TTSCache:
    """
    Singleton disk cache for TTS audio outputs.
    Keys are deterministic SHA256 hashes of text, engine, voice reference, and generation parameters.
    """

    _instance = None
    _lock = threading.Lock()

    def __init__(self, cache_dir: Optional[str] = None):
        self._cache_dir = cache_dir or os.path.join(AUDIO_DIR, "cache")
        os.makedirs(self._cache_dir, exist_ok=True)
        self._hits = 0
        self._misses = 0
        self._io_lock = threading.Lock()
        logger.debug("TTS_CACHE", f"TTSCache initialized at: {self._cache_dir}")

    @classmethod
    def get_instance(cls) -> "TTSCache":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ── Configuration & Status ───────────────────────────────────────────────

    def is_enabled(self) -> bool:
        """Checks if TTS caching is globally enabled in audio config."""
        try:
            from hecos.core.audio.device_manager import get_audio_config
            acfg = get_audio_config()
            return bool(acfg.get("tts_cache_enabled", True))
        except Exception:
            return True

    def get_max_size_mb(self) -> int:
        """Returns maximum cache size in MB from audio config (default 500 MB)."""
        try:
            from hecos.core.audio.device_manager import get_audio_config
            acfg = get_audio_config()
            return int(acfg.get("tts_cache_max_mb", 500))
        except Exception:
            return 500

    # ── Key Computation ──────────────────────────────────────────────────────

    @staticmethod
    def _extract_voice_and_params(engine: str, session_overrides: Optional[dict] = None) -> tuple[str, dict]:
        """Extracts voice identifier and relevant inference parameters for caching."""
        overrides = session_overrides or {}
        engine_clean = (engine or "").lower().strip()

        voice = ""
        params: Dict[str, Any] = {}

        if engine_clean in ("fish_speech", "fish"):
            voice = (
                overrides.get("fish_reference_audio")
                or overrides.get("fish_reference_id")
                or overrides.get("tts_voice")
                or ""
            )
            for k in ("fish_temperature", "fish_top_p", "fish_repetition_penalty", "fish_chunk_length", "fish_chunk_sentences", "fish_volume", "fish_norm"):
                if k in overrides and overrides[k] is not None:
                    params[k] = overrides[k]
        elif engine_clean in ("xtts2", "xtts"):
            voice = overrides.get("speaker_wav") or overrides.get("speaker") or overrides.get("tts_voice") or ""
            for k in ("temperature", "speed", "repetition_penalty", "top_p", "top_k"):
                if k in overrides and overrides[k] is not None:
                    params[k] = overrides[k]
        elif engine_clean == "kokoro":
            voice = overrides.get("kokoro_voice") or overrides.get("voice") or overrides.get("tts_voice") or ""
            if "speed" in overrides:
                params["speed"] = overrides["speed"]
        elif engine_clean == "piper":
            voice = overrides.get("onnx_model") or overrides.get("tts_voice") or ""
            for k in ("speed", "noise_scale", "noise_w"):
                if k in overrides and overrides[k] is not None:
                    params[k] = overrides[k]
        else:
            voice = overrides.get("tts_voice") or ""

        return str(voice).strip(), params

    def compute_key(
        self,
        text: str,
        engine: str = "",
        voice: str = "",
        params: Optional[dict] = None,
        session_overrides: Optional[dict] = None
    ) -> str:
        """
        Generates a deterministic SHA256 cache key.
        """
        norm_text = " ".join(text.strip().split())
        eng = (engine or "").lower().strip()

        extracted_voice, extracted_params = self._extract_voice_and_params(eng, session_overrides)
        final_voice = voice.strip() if voice else extracted_voice

        final_params = dict(extracted_params)
        if params:
            final_params.update(params)

        payload = {
            "text": norm_text,
            "engine": eng,
            "voice": final_voice,
            "params": final_params
        }
        serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    # ── Cache Lookup & Store (File-based) ─────────────────────────────────────

    def get_to_file(
        self,
        text: str,
        engine: str,
        out_filepath: str,
        voice: str = "",
        session_overrides: Optional[dict] = None
    ) -> bool:
        """
        If a cached audio file exists for the request, copies it to `out_filepath` and returns True.
        """
        if not self.is_enabled() or not text:
            return False

        key = self.compute_key(text, engine=engine, voice=voice, session_overrides=session_overrides)
        cache_path = os.path.join(self._cache_dir, f"{key}.wav")

        with self._io_lock:
            if os.path.exists(cache_path) and os.path.getsize(cache_path) > 44:
                try:
                    os.makedirs(os.path.dirname(os.path.abspath(out_filepath)), exist_ok=True)
                    shutil.copy2(cache_path, out_filepath)
                    # Update accessed time for LRU
                    os.utime(cache_path, None)
                    self._hits += 1
                    logger.info("TTS_CACHE", f"⚡ CACHE HIT [{engine}] (key={key[:8]}): copied {os.path.getsize(cache_path)} bytes to {os.path.basename(out_filepath)}")
                    return True
                except Exception as e:
                    logger.warning("TTS_CACHE", f"Failed to copy from cache: {e}")

        self._misses += 1
        return False

    def put_from_file(
        self,
        text: str,
        engine: str,
        source_filepath: str,
        voice: str = "",
        session_overrides: Optional[dict] = None
    ) -> Optional[str]:
        """
        Stores an audio file into the cache.
        """
        if not self.is_enabled() or not text:
            return None

        if not os.path.exists(source_filepath) or os.path.getsize(source_filepath) <= 44:
            return None

        key = self.compute_key(text, engine=engine, voice=voice, session_overrides=session_overrides)
        target_path = os.path.join(self._cache_dir, f"{key}.wav")
        meta_path = os.path.join(self._cache_dir, f"{key}.json")

        with self._io_lock:
            try:
                # Atomic copy via temp file in same directory
                tmp_fd, tmp_path = tempfile.mkstemp(dir=self._cache_dir, prefix=f"cache_{key[:6]}_", suffix=".tmp")
                os.close(tmp_fd)
                shutil.copy2(source_filepath, tmp_path)
                os.replace(tmp_path, target_path)

                # Save metadata for inspection
                metadata = {
                    "key": key,
                    "engine": engine,
                    "text_preview": text[:120],
                    "timestamp": time.time(),
                    "size_bytes": os.path.getsize(target_path)
                }
                with open(meta_path, "w", encoding="utf-8") as mf:
                    json.dump(metadata, mf, indent=2, ensure_ascii=False)

                logger.debug("TTS_CACHE", f"Stored {os.path.getsize(target_path)} bytes in cache (key={key[:8]})")
            except Exception as e:
                logger.warning("TTS_CACHE", f"Failed to store audio in cache: {e}")
                return None

        # Asynchronous cleanup if size limit exceeded
        threading.Thread(target=self._maybe_evict_lru, daemon=True).start()
        return target_path

    # ── Cache Lookup & Store (Bytes-based for chunk synthesis) ────────────────

    def get_bytes(
        self,
        text: str,
        engine: str,
        voice: str = "",
        session_overrides: Optional[dict] = None
    ) -> Optional[bytes]:
        """
        Retrieves raw WAV bytes from cache if present.
        """
        if not self.is_enabled() or not text:
            return None

        key = self.compute_key(text, engine=engine, voice=voice, session_overrides=session_overrides)
        cache_path = os.path.join(self._cache_dir, f"{key}.wav")

        with self._io_lock:
            if os.path.exists(cache_path) and os.path.getsize(cache_path) > 44:
                try:
                    with open(cache_path, "rb") as f:
                        data = f.read()
                    os.utime(cache_path, None)
                    self._hits += 1
                    logger.info("TTS_CACHE", f"⚡ CACHE HIT [chunk] ({len(data)} bytes, key={key[:8]})")
                    return data
                except Exception as e:
                    logger.warning("TTS_CACHE", f"Failed to read bytes from cache: {e}")

        self._misses += 1
        return None

    def put_bytes(
        self,
        text: str,
        engine: str,
        audio_bytes: bytes,
        voice: str = "",
        session_overrides: Optional[dict] = None
    ) -> Optional[str]:
        """
        Stores raw WAV bytes into cache.
        """
        if not self.is_enabled() or not text or not audio_bytes or len(audio_bytes) <= 44:
            return None

        key = self.compute_key(text, engine=engine, voice=voice, session_overrides=session_overrides)
        target_path = os.path.join(self._cache_dir, f"{key}.wav")

        with self._io_lock:
            try:
                tmp_fd, tmp_path = tempfile.mkstemp(dir=self._cache_dir, prefix=f"chunk_{key[:6]}_", suffix=".tmp")
                with os.fdopen(tmp_fd, "wb") as f:
                    f.write(audio_bytes)
                os.replace(tmp_path, target_path)
                logger.debug("TTS_CACHE", f"Stored {len(audio_bytes)} chunk bytes in cache (key={key[:8]})")
            except Exception as e:
                logger.warning("TTS_CACHE", f"Failed to write chunk bytes to cache: {e}")
                return None

        threading.Thread(target=self._maybe_evict_lru, daemon=True).start()
        return target_path

    # ── Eviction & Maintenance ───────────────────────────────────────────────

    def _maybe_evict_lru(self):
        """Evicts oldest accessed cache files when cache exceeds max size."""
        try:
            max_mb = self.get_max_size_mb()
            max_bytes = max_mb * 1024 * 1024

            with self._io_lock:
                wav_files = glob.glob(os.path.join(self._cache_dir, "*.wav"))
                total_bytes = sum(os.path.getsize(f) for f in wav_files if os.path.exists(f))

                if total_bytes <= max_bytes:
                    return

                # Sort files by atime (least recently accessed first)
                entries = []
                for f in wav_files:
                    try:
                        st = os.stat(f)
                        entries.append((st.st_atime, st.st_size, f))
                    except Exception:
                        pass

                entries.sort(key=lambda x: x[0])

                deleted_count = 0
                for _, sz, filepath in entries:
                    if total_bytes <= max_bytes * 0.8:  # Evict down to 80% watermark
                        break
                    try:
                        os.remove(filepath)
                        total_bytes -= sz
                        deleted_count += 1
                        meta = filepath[:-4] + ".json"
                        if os.path.exists(meta):
                            os.remove(meta)
                    except Exception:
                        pass

                if deleted_count > 0:
                    logger.info("TTS_CACHE", f"LRU eviction: deleted {deleted_count} stale cache file(s).")
        except Exception as e:
            logger.debug("TTS_CACHE", f"Eviction error: {e}")

    def clear(self) -> int:
        """Purges all files in the cache directory."""
        count = 0
        with self._io_lock:
            for pattern in ("*.wav", "*.json", "*.tmp"):
                for f in glob.glob(os.path.join(self._cache_dir, pattern)):
                    try:
                        os.remove(f)
                        count += 1
                    except Exception:
                        pass
        self._hits = 0
        self._misses = 0
        logger.info("TTS_CACHE", f"Cleared {count} cache file(s).")
        return count

    def get_stats(self) -> dict:
        """Returns cache telemetry: enabled status, file count, disk usage, hit/miss counters."""
        with self._io_lock:
            wav_files = glob.glob(os.path.join(self._cache_dir, "*.wav"))
            total_bytes = sum(os.path.getsize(f) for f in wav_files if os.path.exists(f))
            return {
                "enabled": self.is_enabled(),
                "file_count": len(wav_files),
                "total_size_mb": round(total_bytes / (1024 * 1024), 2),
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate_pct": round((self._hits / max(self._hits + self._misses, 1)) * 100, 1)
            }
