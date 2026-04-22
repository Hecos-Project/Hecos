"""
MODULE: Voice (TTS) - Zentra Core
DESCRIPTION: Piper TTS engine. Uses sounddevice for audio output on the selected device.
             Falls back to winsound if sounddevice is not available.
"""

import subprocess
import os
import json
import time
import keyboard
import msvcrt

from zentra.core.logging import logger
from zentra.core.constants import AUDIO_DIR
import os as _os
_os.makedirs(AUDIO_DIR, exist_ok=True)
_RISPOSTA_WAV = _os.path.join(AUDIO_DIR, "risposta.wav")

def _get_project_root():
    # c:\Zentra-Core\zentra\core\audio\voice.py -> c:\Zentra-Core
    current_file = _os.path.abspath(__file__)
    # Go up 4 levels to reach the project root
    root = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.dirname(current_file))))
    return _os.path.normpath(root)

is_speaking = False
_current_piper_proc = None

# --- sounddevice optional import ---
try:
    import sounddevice as sd
    import soundfile as sf
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False
    import winsound  # fallback


def _play_wav(wav_path: str, device_index: int = -1):
    """
    Plays a WAV file on the specified output device.
    Uses sounddevice if available, otherwise falls back to winsound.
    Returns estimated duration in seconds.
    """
    if SOUNDDEVICE_AVAILABLE:
        try:
            data, sample_rate = sf.read(wav_path, dtype="float32")
            kwargs = {"samplerate": sample_rate, "blocking": False}
            if device_index >= 0:
                kwargs["device"] = device_index
            sd.play(data, **kwargs)
            return len(data) / sample_rate
        except Exception as e:
            # More descriptive error for device index issues
            error_msg = str(e)
            if "Invalid device" in error_msg or "PaErrorCode -9996" in error_msg:
                logger.info("VOICE", f"sounddevice error: Invalid Output Device (index {device_index}). "
                            f"Please check your Speaker selection in config_audio.json. Falling back to winsound...")
            else:
                logger.debug("VOICE", f"sounddevice playback error: {e} — falling back to winsound")
            # Fall through to winsound below
    # Fallback: winsound (no device selection, async)
    import winsound as ws
    ws.PlaySound(wav_path, ws.SND_FILENAME | ws.SND_ASYNC)
    return None  # duration unknown


def speak(text, state=None):
    global is_speaking
    if not text:
        return

    # 1. Load Audio Configuration
    try:
        from zentra.core.audio.device_manager import get_audio_config
        audio_cfg = get_audio_config()
        
        # Check if voice is globally disabled
        if not audio_cfg.get("voice_status", True):
            return
            
        output_device    = audio_cfg.get("output_device_index", -1)
        
        # --- DYNAMIC PATH RESOLUTION ---
        root = _get_project_root()
        default_piper = _os.path.join(root, "bin", "piper", "piper.exe")
        default_model = _os.path.join(root, "bin", "piper", "it_IT-paola-medium.onnx")

        piper_path    = audio_cfg.get("piper_path", default_piper)
        model_path    = audio_cfg.get("onnx_model", default_model)

        # 3. Validation and Fallback to defaults
        # If the configured piper_path doesn't exist, we MUST fallback to the default internal path
        if not _os.path.exists(piper_path):
            if _os.path.exists(default_piper):
                logger.debug("VOICE", f"Configured Piper path '{piper_path}' not found. Falling back to default: {default_piper}")
                piper_path = default_piper
            else:
                logger.error("VOICE", f"Piper executable not found at configured path OR default project path ({default_piper})")

        if not _os.path.exists(model_path):
            if _os.path.exists(default_model):
                logger.debug("VOICE", f"Configured model path '{model_path}' not found. Falling back to default: {default_model}")
                model_path = default_model
            else:
                logger.error("VOICE", f"ONNX model not found at configured path OR default project path ({default_model})")

        # 4. Extract and Round TTS Parameters
        # length_scale is inverse of speed (e.g. speed 1.2 -> 0.833 duration multiplier)
        speed            = audio_cfg.get("speed", 1.0)
        length_scale     = round(1.0 / speed, 3) if speed > 0 else 1.0
        noise_scale      = round(audio_cfg.get("noise_scale", 0.667), 3)
        noise_w          = round(audio_cfg.get("noise_w", 0.8), 3)
        sentence_silence = round(audio_cfg.get("sentence_silence", 0.2), 3)

    except Exception as e:
        logger.debug("VOICE", f"Configuration error: {e}")
        root = _get_project_root()
        length_scale, noise_scale, noise_w, sentence_silence = 1.0, 0.667, 0.8, 0.2
        piper_path = _os.path.join(root, "bin", "piper", "piper.exe")
        model_path = _os.path.join(root, "bin", "piper", "it_IT-paola-medium.onnx")
        output_device = -1

    is_speaking = True
    if state:
        state.system_speaking = True

    global _current_piper_proc
    try:
        clean_text = text.replace('"', "").replace("\n", " ")

        command = [
            piper_path, "-m", model_path,
            "--length_scale",    str(length_scale),
            "--noise_scale",     str(noise_scale),
            "--noise_w",         str(noise_w),
            "--sentence_silence", str(sentence_silence),
            "-f", _RISPOSTA_WAV
        ]

        proc = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False
        )
        _current_piper_proc = proc
        stdout, stderr = proc.communicate(input=clean_text.encode('utf-8'))
        _current_piper_proc = None

        if proc.returncode != 0:
            error_msg = stderr.decode('utf-8', errors='ignore')
            logger.error("VOICE", f"Piper synthesis failed (code {proc.returncode}): {error_msg}")
            return

        if not is_speaking:
            logger.debug("VOICE", "Generation interrupted by user.")
            return

        wav_path = _RISPOSTA_WAV
        if os.path.exists(wav_path):
            actual_duration = _play_wav(wav_path, device_index=output_device)

            if actual_duration is not None:
                # sounddevice async path: wait exactly actual_duration, checking for stops
                start_time = time.time()
                while (time.time() - start_time) < actual_duration:
                    if not is_speaking:  # API stop_voice() sets this to False
                        sd.stop()
                        break
                    if keyboard.is_pressed("esc"):
                        while msvcrt.kbhit(): msvcrt.getch()
                        if state: state.last_voice_stop = time.time()
                        stop_voice()
                        break
                    time.sleep(0.05)
            else:
                # winsound async path: estimate duration then watch for ESC
                estimated_duration = (len(clean_text) / 12) * length_scale + sentence_silence
                start_time = time.time()
                while (time.time() - start_time) < estimated_duration:
                    if not is_speaking:
                        break
                    if keyboard.is_pressed("esc"):
                        while msvcrt.kbhit(): msvcrt.getch()
                        if state: state.last_voice_stop = time.time()
                        stop_voice()
                        break
                    time.sleep(0.05)

    except Exception as e:
        logger.info("VOICE", f"Piper execution error: {e}")
    finally:
        time.sleep(0.3)
        is_speaking = False
        if state:
            state.system_speaking = False


def stop_voice():
    global is_speaking, _current_piper_proc
    logger.debug("VOICE", "stop_voice() called - Attempting to silence all PC speaker audio...")
    
    # Kill generation if it's currently running
    if _current_piper_proc is not None:
        try:
            logger.debug("VOICE", f"Terminating Piper process {_current_piper_proc.pid}...")
            _current_piper_proc.terminate()
        except Exception as e:
            logger.debug("VOICE", f"Error terminating Piper: {e}")
        finally:
            _current_piper_proc = None

    if SOUNDDEVICE_AVAILABLE:
        try:
            logger.debug("VOICE", "Calling sd.stop()...")
            sd.stop()
        except Exception as e:
            logger.debug("VOICE", f"sd.stop() error: {e}")

    # Always try winsound purge on Windows in case of fallback
    try:
        import winsound as ws
        logger.debug("VOICE", "Calling winsound PURGE...")
        ws.PlaySound(None, ws.SND_PURGE)
    except Exception:
        pass
    
    is_speaking = False
    logger.debug("VOICE", "stop_voice() complete. is_speaking set to False.")