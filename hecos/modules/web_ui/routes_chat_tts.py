"""
routes_chat_tts.py
────────────────────────────────────────────────────────────────────────────
Hecos WebUI — TTS (Piper) Engine for Chat
Provides:
  generate_voice_streaming()  → console-style chunk-by-chunk synthesis
  generate_voice_file()       → legacy single-file synthesis (kept for compat)
  stop_voice_generation()     → kills active Piper process (delegated)
  set_last_audio_path()       → updates the global path consumed by /api/audio
  _maybe_generate_tts()       → orchestrates TTS generation for the chat route
────────────────────────────────────────────────────────────────────────────
"""
import os
import logging
from hecos.core.constants import AUDIO_DIR

_chat_log = logging.getLogger("HecosChatRoutes")

_last_audio_path = None

# ── Chunk registry ────────────────────────────────────────────────────────
# Maps chunk_id → absolute path of the temp WAV file.
# Entries are popped when the file is served (/api/audio/chunk/<id>).
_chunk_registry: dict = {}


def set_last_audio_path(path: str):
    global _last_audio_path
    _last_audio_path = path
    _chat_log.info(f"[Audio] Global _last_audio_path updated to: {path}")


def get_last_audio_path() -> str:
    return _last_audio_path


def get_chunk_path(chunk_id: str) -> str | None:
    """Returns the WAV path for the given chunk_id, or None if not found."""
    return _chunk_registry.get(chunk_id)


def consume_chunk(chunk_id: str) -> str | None:
    """Pops and returns the WAV path (caller is responsible for cleanup)."""
    return _chunk_registry.pop(chunk_id, None)


_tts_jobs = {}


def get_tts_progress(job_id: str) -> dict:
    return _tts_jobs.get(job_id, None)


def generate_voice_file(text: str, voice_cfg: dict, job_id: str = None) -> str:
    """
    Legacy single-file generation (kept for compatibility and fallback).
    For streaming use generate_voice_streaming() instead.
    """
    try:
        out = os.path.join(AUDIO_DIR, "risposta.wav")
        from hecos.core.audio.piper_daemon import get_daemon
        daemon = get_daemon()

        _chat_log.info("[Audio] WebUI generating WAV via in-memory PiperDaemon (legacy)...")

        if job_id:
            _tts_jobs[job_id] = {"current": 0, "total": 1, "status": "generating"}

            def progress_callback(current, total):
                _tts_jobs[job_id]["current"] = current
                _tts_jobs[job_id]["total"] = total
                if current == total:
                    _tts_jobs[job_id]["status"] = "done"

            success = daemon.generate_wav_chunked(text, out, progress_callback)
        else:
            success = daemon.generate_wav_chunked(text, out)

        if success:
            _chat_log.info("[Audio] Legacy WAV generation successful.")
            return out
        else:
            _chat_log.error("[Audio] Legacy WAV generation failed.")
            if job_id and job_id in _tts_jobs:
                _tts_jobs[job_id]["status"] = "error"
            return None

    except Exception as e:
        _chat_log.error(f"[Audio] generate_voice_file error: {e}")
        if job_id and job_id in _tts_jobs:
            _tts_jobs[job_id]["status"] = "error"
        return None


def generate_voice_streaming(text: str, chunk_ready_sse_callback, stop_check=None):
    """
    Console-style streaming synthesis for the WebUI.
    For each sentence synthesized, registers the chunk WAV in _chunk_registry
    and calls chunk_ready_sse_callback(chunk_id, index, total) so the
    inference route can push an SSE 'audio_chunk' event immediately.

    The browser fetches /api/audio/chunk/<chunk_id> and plays chunks in order.
    """
    import uuid as _uuid

    try:
        from hecos.core.audio.piper_daemon import get_daemon
        daemon = get_daemon()

        temp_dir = os.path.join(AUDIO_DIR, "temp_tts")
        os.makedirs(temp_dir, exist_ok=True)

        sent_chunks = []

        def _on_chunk_ready(chunk_path: str, index: int, total: int):
            chunk_id = _uuid.uuid4().hex
            _chunk_registry[chunk_id] = chunk_path
            sent_chunks.append(chunk_id)
            _chat_log.info(f"[Audio] Streaming chunk {index+1}/{total} ready → id={chunk_id[:8]}")
            try:
                chunk_ready_sse_callback(chunk_id, index, total)
            except Exception as e:
                _chat_log.error(f"[Audio] SSE callback error: {e}")

        success = daemon.generate_wav_streaming(
            text, temp_dir, _on_chunk_ready, stop_check=stop_check
        )

        return success, len(sent_chunks)

    except Exception as e:
        _chat_log.error(f"[Audio] generate_voice_streaming error: {e}")
        return False, 0


def stop_voice_generation():
    """Immediately kills any active Piper generation for the browser output."""
    try:
        from hecos.core.audio.piper_daemon import get_daemon
        get_daemon().stop()
        _chat_log.info("[Audio] Called PiperDaemon.stop() from WebUI.")
    except Exception as e:
        _chat_log.error(f"[Audio] Failed to terminate web Piper: {e}")


def _maybe_generate_tts(text: str, cfg_mgr, session_queue=None) -> str:
    """
    Generate TTS audio for the WebUI.
    If session_queue is provided, uses console-style streaming (audio_chunk events).
    Falls back to legacy single-file mode if streaming fails or queue not available.
    Returns "web_stream", "web" or None.
    """
    global _last_audio_path
    try:
        from hecos.core.audio.device_manager import get_audio_config
        voice_cfg = get_audio_config()
        if not voice_cfg.get("voice_status", True):
            _chat_log.debug("[Chat] TTS skipped: voice_status=False.")
            return None

        if session_queue is not None:
            # ── Streaming mode (console-style) ────────────────────────────
            def _sse_push(chunk_id, index, total):
                session_queue.put({
                    "type": "audio_chunk",
                    "chunk_id": chunk_id,
                    "index": index,
                    "total": total
                })

            success, n = generate_voice_streaming(text, _sse_push)
            if success and n > 0:
                return "web_stream"
            # Fallback to legacy if streaming failed
            _chat_log.warning("[Chat] Streaming TTS failed, falling back to legacy mode.")

        # ── Legacy mode ───────────────────────────────────────────────────
        path = generate_voice_file(text, voice_cfg)
        if path:
            _last_audio_path = path
            _chat_log.info(f"[Chat] TTS → browser WAV: {path}")
            return "web"
        return None
    except Exception as e:
        _chat_log.debug(f"[Chat] TTS error: {e}")
        return None
