"""
routes_chat_tts.py
────────────────────────────────────────────────────────────────────────────
Hecos WebUI — TTS (Piper) Engine for Chat
Provides:
  generate_voice_file()   → runs Piper, returns path to WAV
  stop_voice_generation() → kills active Piper process
  set_last_audio_path()   → updates the global path consumed by /api/audio
  _maybe_generate_tts()   → orchestrates TTS generation for the chat route
────────────────────────────────────────────────────────────────────────────
"""
import os
import sys
import logging
import subprocess
from hecos.core.constants import AUDIO_DIR

_chat_log = logging.getLogger("HecosChatRoutes")

_last_audio_path    = None
_current_piper_proc = None


def set_last_audio_path(path: str):
    global _last_audio_path
    _last_audio_path = path
    _chat_log.info(f"[Audio] Global _last_audio_path updated to: {path}")


def get_last_audio_path() -> str:
    return _last_audio_path


def generate_voice_file(text: str, voice_cfg: dict) -> str:
    """
    Runs Piper and creates risposta.wav.
    Returns the absolute path to the generated WAV, or None on failure.
    """
    global _current_piper_proc
    try:
        hecos_root        = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        default_piper_dir = os.path.join(hecos_root, "bin", "piper")
        piper_exe_name    = "piper.exe" if os.name == "nt" else "piper"
        default_piper     = os.path.join(default_piper_dir, piper_exe_name)
        default_model     = os.path.join(default_piper_dir, "it_IT-paola-medium.onnx")

        piper_path = voice_cfg.get("piper_path", default_piper)
        model_path = voice_cfg.get("onnx_model", default_model)

        if not piper_path or not os.path.exists(piper_path):
            if os.path.exists(default_piper):
                piper_path = default_piper
            else:
                _chat_log.info(f"[Audio] Piper executable not found at {piper_path}")
                return None

        if not model_path or not os.path.exists(model_path):
            if os.path.exists(default_model):
                model_path = default_model
            else:
                _chat_log.info(f"[Audio] ONNX model not found at {model_path}")
                return None

        length_scale     = round(1.0 / max(0.1, voice_cfg.get("speed", 1.0)), 3)
        noise_scale      = round(voice_cfg.get("noise_scale", 0.667), 3)
        noise_w          = round(voice_cfg.get("noise_w", 0.8), 3)
        sentence_silence = round(voice_cfg.get("sentence_silence", 0.2), 3)

        out     = os.path.join(AUDIO_DIR, "risposta.wav")
        clean   = text.replace('"', "").replace("\n", " ")
        command = [
            piper_path, "-m", model_path,
            "--length_scale",     str(length_scale),
            "--noise_scale",      str(noise_scale),
            "--noise_w",          str(noise_w),
            "--sentence_silence", str(sentence_silence),
            "-f", out,
        ]

        _chat_log.info(f"[Audio] Piper command: {' '.join(command)}")

        kwargs = {"stdin": subprocess.PIPE, "stdout": subprocess.PIPE, "stderr": subprocess.PIPE}
        if sys.platform == "win32":
            kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW

        proc = subprocess.Popen(command, **kwargs)
        _current_piper_proc = proc

        try:
            timeout = voice_cfg.get("piper_timeout", 180)
            _, stderr = proc.communicate(input=clean.encode("utf-8"), timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()
            _chat_log.error(f"[Audio] Piper TTS timed out after {timeout}s")
            return None
        finally:
            _current_piper_proc = None

        if proc.returncode != 0:
            _chat_log.error(f"[Audio] Piper failed (code {proc.returncode}): {stderr.decode('utf-8', errors='ignore')}")
            return None

        return out if os.path.exists(out) else None

    except Exception as e:
        _chat_log.error(f"[Audio] generate_voice_file error: {e}")
        return None


def stop_voice_generation():
    """Immediately kills any active Piper generation for the browser output."""
    global _current_piper_proc
    if _current_piper_proc is not None:
        try:
            pid = _current_piper_proc.pid
            _chat_log.info(f"[Audio] Killing active web Piper process {pid}...")
            _current_piper_proc.terminate()
        except Exception as e:
            _chat_log.error(f"[Audio] Failed to terminate web Piper: {e}")
        finally:
            _current_piper_proc = None


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
