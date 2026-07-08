"""
routes_chat_tts.py
────────────────────────────────────────────────────────────────────────────
Hecos WebUI — TTS (Piper) Engine for Chat
Provides:
  generate_voice_file()   → runs PiperDaemon, returns path to WAV
  stop_voice_generation() → kills active Piper process (delegated)
  set_last_audio_path()   → updates the global path consumed by /api/audio
  _maybe_generate_tts()   → orchestrates TTS generation for the chat route
────────────────────────────────────────────────────────────────────────────
"""
import os
import sys
import logging
from hecos.core.constants import AUDIO_DIR

_chat_log = logging.getLogger("HecosChatRoutes")

_last_audio_path    = None


def set_last_audio_path(path: str):
    global _last_audio_path
    _last_audio_path = path
    _chat_log.info(f"[Audio] Global _last_audio_path updated to: {path}")


def get_last_audio_path() -> str:
    return _last_audio_path


_tts_jobs = {}

def get_tts_progress(job_id: str) -> dict:
    return _tts_jobs.get(job_id, None)

def generate_voice_file(text: str, voice_cfg: dict, job_id: str = None) -> str:
    """
    Runs PiperDaemon in-memory synthesis and creates risposta.wav instantly.
    Returns the absolute path to the generated WAV, or None on failure.
    """
    try:
        out = os.path.join(AUDIO_DIR, "risposta.wav")
        from hecos.core.audio.piper_daemon import get_daemon
        daemon = get_daemon()
        
        _chat_log.info("[Audio] WebUI generating WAV via in-memory PiperDaemon...")
        
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
            _chat_log.info("[Audio] Native in-memory WAV generation successful.")
            return out
        else:
            _chat_log.error("[Audio] Native in-memory WAV generation failed.")
            if job_id and job_id in _tts_jobs:
                _tts_jobs[job_id]["status"] = "error"
            return None
            
    except Exception as e:
        _chat_log.error(f"[Audio] generate_voice_file error: {e}")
        if job_id and job_id in _tts_jobs:
            _tts_jobs[job_id]["status"] = "error"
        return None


def stop_voice_generation():
    """Immediately kills any active Piper generation for the browser output."""
    try:
        from hecos.core.audio.piper_daemon import get_daemon
        get_daemon().stop()
        _chat_log.info("[Audio] Called PiperDaemon.stop() from WebUI.")
    except Exception as e:
        _chat_log.error(f"[Audio] Failed to terminate web Piper: {e}")


def _maybe_generate_tts(text: str, cfg_mgr) -> str:
    """
    Generate TTS audio for the WebUI.
    Returns "web" if the WAV was generated, None otherwise.
    """
    global _last_audio_path
    try:
        from hecos.core.audio.device_manager import get_audio_config
        voice_cfg = get_audio_config()
        if not voice_cfg.get("voice_status", True):
            _chat_log.debug("[Chat] TTS skipped: voice_status=False.")
            return None

        path = generate_voice_file(text, voice_cfg)
        if path:
            _last_audio_path = path
            _chat_log.info(f"[Chat] TTS → browser WAV: {path}")
            return "web"
        return None
    except Exception as e:
        _chat_log.debug(f"[Chat] TTS error: {e}")
        return None
