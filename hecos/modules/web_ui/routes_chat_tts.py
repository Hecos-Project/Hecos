"""
routes_chat_tts.py
────────────────────────────────────────────────────────────────────────────
Hecos WebUI — TTS (Piper) Engine for Chat
Provides:
  generate_voice_file()        → runs PiperDaemon, returns (path, audio_id)
  stop_voice_generation()      → kills active Piper process (delegated)
  set_last_audio_path()        → updates the global path consumed by /api/audio
  get_audio_history_path()     → returns path inside media/audio/history/
  cleanup_audio_history()      → prunes oldest WAVs beyond max_files limit
  cleanup_temp_tts()           → removes orphaned temp_tts chunks on startup
  _maybe_generate_tts()        → orchestrates TTS generation for the chat route
────────────────────────────────────────────────────────────────────────────
"""
import os
import uuid
import glob
import logging
from hecos.core.constants import AUDIO_DIR

_chat_log = logging.getLogger("HecosChatRoutes")

_last_audio_path = None
_last_audio_id   = None   # UUID basename (no extension) of the last generated file

# ── Sub-directories ────────────────────────────────────────────────────────────
HISTORY_DIR = os.path.join(AUDIO_DIR, "history")
TEMP_DIR    = os.path.join(AUDIO_DIR, "temp_tts")


def _ensure_dirs():
    os.makedirs(HISTORY_DIR, exist_ok=True)
    os.makedirs(TEMP_DIR,    exist_ok=True)


def set_last_audio_path(path: str, audio_id: str = None):
    global _last_audio_path, _last_audio_id
    _last_audio_path = path
    _last_audio_id   = audio_id
    _chat_log.info(f"[Audio] Global _last_audio_path updated to: {path}")


def get_last_audio_path() -> str:
    return _last_audio_path


def get_last_audio_id() -> str:
    return _last_audio_id


def get_audio_history_path(audio_id: str) -> str | None:
    """Returns the absolute path for a stored history WAV, or None if it doesn't exist."""
    if not audio_id:
        return None
    path = os.path.join(HISTORY_DIR, f"{audio_id}.wav")
    return path if os.path.exists(path) else None


# ── Cleanup helpers ────────────────────────────────────────────────────────────

def cleanup_temp_tts():
    """Delete any leftover chunk files from temp_tts (crash survivors)."""
    try:
        _ensure_dirs()
        files = glob.glob(os.path.join(TEMP_DIR, "chunk_*.wav"))
        for f in files:
            try:
                os.remove(f)
            except Exception:
                pass
        if files:
            _chat_log.info(f"[Audio] Cleaned {len(files)} orphaned temp_tts chunk(s).")
    except Exception as e:
        _chat_log.warning(f"[Audio] cleanup_temp_tts error: {e}")


def cleanup_audio_history(max_files: int = 100):
    """
    Prune oldest WAV files in history/ so that at most max_files are kept.
    Called automatically after each successful TTS generation.
    """
    try:
        _ensure_dirs()
        files = sorted(
            glob.glob(os.path.join(HISTORY_DIR, "*.wav")),
            key=os.path.getmtime
        )
        excess = len(files) - max_files
        if excess > 0:
            for f in files[:excess]:
                try:
                    os.remove(f)
                    _chat_log.debug(f"[Audio] Pruned old history WAV: {f}")
                except Exception:
                    pass
            _chat_log.info(f"[Audio] Pruned {excess} old history WAV(s), keeping {max_files}.")
    except Exception as e:
        _chat_log.warning(f"[Audio] cleanup_audio_history error: {e}")


# ── Progress tracking ──────────────────────────────────────────────────────────

_tts_jobs = {}


def get_tts_progress(job_id: str) -> dict:
    return _tts_jobs.get(job_id, None)


# ── Core generation ────────────────────────────────────────────────────────────

def generate_voice_file(text: str, voice_cfg: dict, job_id: str = None) -> tuple[str | None, str | None]:
    """
    Runs PiperDaemon in-memory synthesis and stores the WAV in media/audio/history/.
    Returns (absolute_path, audio_id) on success, or (None, None) on failure.
    audio_id is a UUID string usable as a persistent file reference.
    """
    try:
        _ensure_dirs()
        audio_id = uuid.uuid4().hex
        out = os.path.join(HISTORY_DIR, f"{audio_id}.wav")

        from hecos.core.audio.piper_daemon import get_daemon
        daemon = get_daemon()

        _chat_log.info(f"[Audio] WebUI generating WAV id={audio_id} via PiperDaemon...")

        if job_id:
            _tts_jobs[job_id] = {"current": 0, "total": 1, "status": "generating"}
            def progress_callback(current, total):
                _tts_jobs[job_id]["current"] = current
                _tts_jobs[job_id]["total"]   = total
                if current == total:
                    _tts_jobs[job_id]["status"] = "done"
            success = daemon.generate_wav_chunked(text, out, progress_callback)
        else:
            success = daemon.generate_wav_chunked(text, out)

        if success:
            _chat_log.info(f"[Audio] WAV generation successful: {out}")
            # Read max_files from audio config
            try:
                from hecos.core.audio.device_manager import get_audio_config
                acfg = get_audio_config()
                max_f = int(acfg.get("tts_history_max_files", 100))
            except Exception:
                max_f = 100
            cleanup_audio_history(max_f)
            return out, audio_id
        else:
            _chat_log.error("[Audio] WAV generation failed.")
            if job_id and job_id in _tts_jobs:
                _tts_jobs[job_id]["status"] = "error"
            # Remove empty/partial file if created
            try:
                if os.path.exists(out):
                    os.remove(out)
            except Exception:
                pass
            return None, None

    except Exception as e:
        _chat_log.error(f"[Audio] generate_voice_file error: {e}")
        if job_id and job_id in _tts_jobs:
            _tts_jobs[job_id]["status"] = "error"
        return None, None


def stop_voice_generation():
    """Immediately kills any active Piper generation for the browser output."""
    try:
        from hecos.core.audio.piper_daemon import get_daemon
        get_daemon().stop()
        _chat_log.info("[Audio] Called PiperDaemon.stop() from WebUI.")
    except Exception as e:
        _chat_log.error(f"[Audio] Failed to terminate web Piper: {e}")


def _maybe_generate_tts(text: str, cfg_mgr) -> tuple[str | None, str | None]:
    """
    Generate TTS audio for the WebUI.
    Returns ("web", audio_id) if the WAV was generated, (None, None) otherwise.
    """
    global _last_audio_path, _last_audio_id
    try:
        from hecos.core.audio.device_manager import get_audio_config
        voice_cfg = get_audio_config()
        if not voice_cfg.get("voice_status", True):
            _chat_log.debug("[Chat] TTS skipped: voice_status=False.")
            return None, None

        path, audio_id = generate_voice_file(text, voice_cfg)
        if path:
            _last_audio_path = path
            _last_audio_id   = audio_id
            _chat_log.info(f"[Chat] TTS → history WAV id={audio_id}: {path}")
            return "web", audio_id
        return None, None
    except Exception as e:
        _chat_log.debug(f"[Chat] TTS error: {e}")
        return None, None

# Automatically clean up orphaned temp files on startup
try:
    cleanup_temp_tts()
except Exception:
    pass

