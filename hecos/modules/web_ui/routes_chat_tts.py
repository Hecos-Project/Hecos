"""
routes_chat_tts.py
────────────────────────────────────────────────────────────────────────────
Hecos WebUI — TTS (Piper/Kokoro/XTTS2) Engine for Chat
Provides:
  generate_voice_file()        → runs TTSManager/XTTS2 Bypass, returns (path, audio_id)
  stop_voice_generation()      → kills active TTS generation (delegated)
  set_last_audio_path()        → updates the global path consumed by /api/audio
  get_audio_history_path()     → returns path inside media/audio/history/
  cleanup_audio_history()      → prunes oldest WAVs beyond max_files limit
  cleanup_temp_tts()           → removes orphaned temp_tts chunks on startup
  _maybe_generate_tts()        → orchestrates TTS generation for the chat route
────────────────────────────────────────────────────────────────────────────
"""
import os
import sys
import re
import uuid
import glob
import logging
import subprocess
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


# ── Text Sanitization for TTS ──────────────────────────────────────────────────

def sanitize_text_for_tts(text: str) -> str:
    """
    Cleans up prompt residues, image tags, Markdown syntax, and unwanted characters
    before sending text to the TTS engine.
    """
    if not text:
        return ""

    try:
        from hecos.core.audio.device_manager import get_audio_config
        acfg = get_audio_config()
    except Exception:
        acfg = {}

    clean_enabled = acfg.get("tts_clean_text", True)
    if not clean_enabled:
        return text

    custom_chars = acfg.get("tts_excluded_chars", "*#_~><|-=\\/^@$%&")

    # 1. Remove agent image tags (e.g. IMG:gen_...)
    text = re.sub(r'IMG:\S+', '', text)
    text = re.sub(r'IMG:.*$', '', text, flags=re.MULTILINE)

    # 2. Remove code blocks and inline code
    text = re.sub(r'```[\s\S]*?```', '', text)
    text = re.sub(r'`[^`]+`', '', text)

    # 3. Remove URLs and handle Markdown links [Text](url)
    text = re.sub(r'https?://\S+|www\.\S+', '', text)
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)

    # 4. Remove Markdown formatting
    text = re.sub(r'\*{1,3}|_{1,3}|~{1,2}', '', text)
    text = re.sub(r'^\s*#{1,6}\s*', '', text, flags=re.MULTILINE)

    # 5. Remove arrows and repeated character sequences
    text = re.sub(r'[-=><~_]{2,}', ' ', text)

    # 6. Remove user-specified custom characters
    if custom_chars:
        escaped_chars = re.escape(custom_chars)
        text = re.sub(rf'[{escaped_chars}]', ' ', text)

    # 7. Final normalization
    text = re.sub(r'\.{2,}', '.', text)
    text = re.sub(r'\s+', ' ', text).strip()

    return text


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


# ── XTTS2 Isolated Bypass Helper ───────────────────────────────────────────────

def _run_xtts2_bypass(text: str, out_path: str, voice_cfg: dict, job_id: str = None) -> bool:
    """
    Executes XTTS2 voice generation in an isolated subprocess with CUDA GPU acceleration,
    monkey-patching torchaudio to load reference WAVs via soundfile (bypassing torchcodec).
    """
    try:
        from hecos.core.audio.device_manager import get_audio_config
        acfg = get_audio_config()
        xtts_cfg = acfg.get('xtts', {})
        speaker_wav = xtts_cfg.get('speaker_wav', '').strip()
        language = xtts_cfg.get('language', 'it')
        speaker = xtts_cfg.get('speaker', 'Claribel Dervla')
        speed = str(xtts_cfg.get('speed', 1.0))
        temperature = str(xtts_cfg.get('temperature', 0.75))
        repetition_penalty = str(xtts_cfg.get('repetition_penalty', 5.0))
        top_k = str(xtts_cfg.get('top_k', 50))
        top_p = str(xtts_cfg.get('top_p', 0.85))
        length_penalty = str(xtts_cfg.get('length_penalty', 1.0))
        gpu_acceleration = xtts_cfg.get('gpu_acceleration', 'auto')  # 'auto', 'gpu', 'cpu'

        _chat_log.info(f"[XTTS2 Bypass] Starting isolated generation. GPU mode: {gpu_acceleration}, Wav target: {out_path}")

        inline_code = (
            "import sys, os\n"
            "import torch\n"
            "try:\n"
            "    import torchaudio\n"
            "    import soundfile as sf\n"
            "    from collections import namedtuple\n"
            "    AudioMetaData = namedtuple('AudioMetaData', ['sample_rate', 'num_frames', 'num_channels', 'bits_per_sample', 'encoding'])\n"
            "    def _sf_load(filepath, *args, **kwargs):\n"
            "        data, sr = sf.read(filepath, dtype='float32')\n"
            "        tensor = torch.from_numpy(data)\n"
            "        if tensor.ndim == 1:\n"
            "            tensor = tensor.unsqueeze(0)\n"
            "        elif tensor.ndim == 2:\n"
            "            tensor = tensor.t()\n"
            "        return tensor, sr\n"
            "    def _sf_info(filepath, *args, **kwargs):\n"
            "        info = sf.info(filepath)\n"
            "        return AudioMetaData(info.samplerate, info.frames, info.channels, 16, 'PCM_S')\n"
            "    torchaudio.load = _sf_load\n"
            "    torchaudio.info = _sf_info\n"
            "except Exception:\n"
            "    pass\n"
            "\n"
            "from TTS.api import TTS\n"
            "text = sys.argv[1]\n"
            "out_path = sys.argv[2]\n"
            "speaker_wav = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] else None\n"
            "lang = sys.argv[4] if len(sys.argv) > 4 and sys.argv[4] else 'it'\n"
            "speaker = sys.argv[5] if len(sys.argv) > 5 and sys.argv[5] else 'Claribel Dervla'\n"
            "speed = float(sys.argv[6]) if len(sys.argv) > 6 else 1.0\n"
            "temperature = float(sys.argv[7]) if len(sys.argv) > 7 else 0.75\n"
            "rep_pen = float(sys.argv[8]) if len(sys.argv) > 8 else 5.0\n"
            "gpu_mode = sys.argv[9] if len(sys.argv) > 9 else 'auto'\n"
            "top_k = int(sys.argv[10]) if len(sys.argv) > 10 else 50\n"
            "top_p = float(sys.argv[11]) if len(sys.argv) > 11 else 0.85\n"
            "length_penalty = float(sys.argv[12]) if len(sys.argv) > 12 else 1.0\n"
            "try:\n"
            "    cuda_available = torch.cuda.is_available()\n"
            "    if gpu_mode == 'gpu':\n"
            "        use_cuda = True\n"
            "    elif gpu_mode == 'cpu':\n"
            "        use_cuda = False\n"
            "    else:  # auto\n"
            "        use_cuda = cuda_available\n"
            "    print(f'[XTTS2 Subprocess] gpu_mode={gpu_mode}, CUDA available={cuda_available}, using_gpu={use_cuda}', file=sys.stderr)\n"
            "    print('PROGRESS: 10', flush=True)\n"
            "    tts = TTS('tts_models/multilingual/multi-dataset/xtts_v2', gpu=use_cuda)\n"
            "    print('PROGRESS: 50', flush=True)\n"
            "    kwargs = {'text': text, 'file_path': out_path, 'language': lang, 'speed': speed, 'temperature': temperature, 'repetition_penalty': rep_pen, 'top_k': top_k, 'top_p': top_p, 'length_penalty': length_penalty}\n"
            "    if speaker_wav and os.path.exists(speaker_wav):\n"
            "        kwargs['speaker_wav'] = speaker_wav\n"
            "    else:\n"
            "        kwargs['speaker'] = speaker\n"
            "    print('PROGRESS: 60', flush=True)\n"
            "    tts.tts_to_file(**kwargs)\n"
            "    print('PROGRESS: 95', flush=True)\n"
            "    sys.exit(0)\n"
            "except Exception as e:\n"
            "    print('XTTS Error:', e, file=sys.stderr)\n"
            "    sys.exit(1)\n"
        )

        args = [
            sys.executable, "-c", inline_code, 
            text, out_path, speaker_wav or "", language, speaker, speed, temperature, repetition_penalty, gpu_acceleration, top_k, top_p, length_penalty
        ]
        proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        
        output_log = []
        for line in proc.stdout:
            output_log.append(line)
            if "PROGRESS:" in line and job_id:
                try:
                    pct = int(line.split("PROGRESS:")[1].strip())
                    if job_id in _tts_jobs:
                        _tts_jobs[job_id]["current"] = pct
                        _tts_jobs[job_id]["total"] = 100
                except Exception:
                    pass
        proc.wait(timeout=180)

        if proc.returncode == 0 and os.path.exists(out_path):
            _chat_log.info("[XTTS2 Bypass] Generation completed successfully.")
            return True
        else:
            _chat_log.error(f"[XTTS2 Bypass] Subprocess error:\n{''.join(output_log)}")
            return False

    except Exception as e:
        _chat_log.error(f"[XTTS2 Bypass] Exception during execution: {e}")
        return False


# ── Core generation ────────────────────────────────────────────────────────────

def generate_voice_file(text: str, voice_cfg: dict, job_id: str = None) -> tuple[str | None, str | None]:
    """
    Runs TTSManager or XTTS2 Bypass synthesis and stores the WAV in media/audio/history/.
    Returns (absolute_path, audio_id) on success, or (None, None) on failure.
    """
    try:
        _ensure_dirs()

        text = sanitize_text_for_tts(text)
        if not text:
            _chat_log.warning("[Audio] Text empty after sanitization. Generation skipped.")
            return None, None

        audio_id = uuid.uuid4().hex
        out = os.path.join(HISTORY_DIR, f"{audio_id}.wav")

        session_overrides = voice_cfg.get('session_overrides') or {}
        override_engine = session_overrides.get('tts_engine')

        try:
            from hecos.core.audio.device_manager import get_audio_config
            _acfg = get_audio_config()
            _engine = override_engine or _acfg.get('active_engine', 'unknown')
            _chat_log.info(f"[Audio] Engine='{_engine}', job_id={job_id}")
        except Exception:
            _engine = override_engine or 'unknown'

        if job_id:
            _tts_jobs[job_id] = {"current": 0, "total": 1, "status": "generating"}

        if _engine in ['xtts2', 'xtts']:
            _chat_log.info("[Audio] Intercepted XTTS2 request. Using isolated bypass...")
            if job_id and job_id in _tts_jobs:
                _tts_jobs[job_id]["total"] = 100  # set scale for XTTS
            success = _run_xtts2_bypass(text, out, voice_cfg, job_id=job_id)
        else:
            from hecos.core.audio.tts_manager import TTSManager

            if job_id:
                def progress_callback(current, total):
                    _tts_jobs[job_id]["current"] = current
                    _tts_jobs[job_id]["total"]   = max(total, 1)

                success = TTSManager.generate_wav_chunked(
                    text, out, progress_callback,
                    session_overrides=session_overrides
                )
            else:
                success = TTSManager.generate_wav_chunked(
                    text, out,
                    session_overrides=session_overrides
                )

        if success:
            if job_id:
                _tts_jobs[job_id].update({"current": 1, "total": 1, "status": "done", "audio_id": audio_id})
            _chat_log.info(f"[Audio] WAV generation successful: {out}")
            
            try:
                from hecos.core.audio.device_manager import get_audio_config
                acfg = get_audio_config()
                max_f = int(acfg.get("tts_history_max_files", 100))
            except Exception:
                max_f = 100
            cleanup_audio_history(max_f)
            return out, audio_id
        else:
            if job_id:
                _tts_jobs[job_id].update({
                    "status": "error",
                    "error": "Audio generation failed. Check server logs."
                })
            _chat_log.error("[Audio] WAV generation failed.")
            try:
                if os.path.exists(out):
                    os.remove(out)
            except Exception:
                pass
            return None, None

    except Exception as e:
        _chat_log.error(f"[Audio] generate_voice_file error: {e}")
        if job_id and job_id in _tts_jobs:
            _tts_jobs[job_id].update({"status": "error", "error": str(e)})
        return None, None


def stop_voice_generation():
    """Immediately kills any active TTS generation for the browser output."""
    try:
        from hecos.core.audio.tts_manager import TTSManager
        TTSManager.stop()
        _chat_log.info("[Audio] Called TTSManager.stop() from WebUI.")
    except Exception as e:
        _chat_log.error(f"[Audio] Failed to terminate web TTS: {e}")


def _maybe_generate_tts(text: str, cfg_mgr, session_overrides: dict = None) -> tuple[str | None, str | None]:
    """
    Generate TTS audio for the WebUI.
    Returns ("web", audio_id) if the WAV was generated, (None, None) otherwise.
    """
    global _last_audio_path, _last_audio_id
    try:
        from hecos.core.audio.device_manager import get_audio_config
        voice_cfg = get_audio_config()
        
        if session_overrides is None:
            ai_cfg = cfg_mgr.config.get("ai", {})
            session_overrides = {
                "tts_engine": ai_cfg.get("tts_engine"),
                "tts_voice": ai_cfg.get("tts_voice")
            }
            
        voice_cfg['session_overrides'] = session_overrides

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