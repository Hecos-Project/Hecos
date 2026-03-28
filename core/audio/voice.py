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
            kwargs = {"samplerate": sample_rate, "blocking": True}
            if device_index >= 0:
                kwargs["device"] = device_index
            sd.play(data, **kwargs)
            # Duration is exact when blocking=True
            return len(data) / sample_rate
        except Exception as e:
            # More descriptive error for device index issues
            error_msg = str(e)
            if "Invalid device" in error_msg or "PaErrorCode -9996" in error_msg:
                print(f"[VOICE] sounddevice error: Invalid Output Device (index {device_index}). "
                      f"Please check your Speaker selection in config_audio.json. Falling back to winsound...")
            else:
                print(f"[VOICE] sounddevice playback error: {e} — falling back to winsound")
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
        from core.audio.device_manager import get_audio_config
        audio_cfg = get_audio_config()
        
        # Check if voice is globally disabled
        if not audio_cfg.get("voice_status", True):
            return
            
        length_scale     = 1.0 / max(0.1, audio_cfg.get("speed", 1.2))
        noise_scale      = audio_cfg.get("noise_scale", 0.667)
        noise_w          = audio_cfg.get("noise_w", 0.8)
        sentence_silence = audio_cfg.get("sentence_silence", 0.2)
        piper_path       = audio_cfg.get("piper_path", r"C:\piper\piper.exe")
        model_path       = audio_cfg.get("onnx_model", r"C:\piper\it_IT-aurora-medium.onnx")
        output_device    = audio_cfg.get("output_device_index", -1)
    except Exception as e:
        print(f"[VOICE] Configuration error: {e}")
        length_scale, noise_scale, noise_w, sentence_silence = 1.0, 0.667, 0.8, 0.2
        piper_path, model_path, output_device = r"C:\piper\piper.exe", r"C:\piper\it_IT-aurora-medium.onnx", -1

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
            "-f", "risposta.wav"
        ]

        proc = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True
        )
        _current_piper_proc = proc
        proc.communicate(input=clean_text)
        _current_piper_proc = None

        if os.path.exists("risposta.wav"):
            actual_duration = _play_wav("risposta.wav", device_index=output_device)

            # If sounddevice returned exact duration, use it; otherwise estimate
            if actual_duration is not None:
                # sounddevice blocking=True already waited — just let finally run
                pass
            else:
                # winsound async path: estimate duration then watch for ESC
                estimated_duration = (len(clean_text) / 12) * length_scale + sentence_silence
                start_time = time.time()
                while (time.time() - start_time) < estimated_duration:
                    if keyboard.is_pressed("esc"):
                        while msvcrt.kbhit():
                            msvcrt.getch()
                        if state:
                            state.last_voice_stop = time.time()
                        stop_voice()
                        break
                    time.sleep(0.05)

    except Exception as e:
        print(f"[VOICE] Piper execution error: {e}")
    finally:
        time.sleep(0.3)
        is_speaking = False
        if state:
            state.system_speaking = False


def stop_voice():
    global is_speaking, _current_piper_proc
    
    # Kill generation if it's currently running
    if _current_piper_proc is not None:
        try:
            _current_piper_proc.terminate()
        except:
            pass
        finally:
            _current_piper_proc = None

    if SOUNDDEVICE_AVAILABLE:
        try:
            sd.stop()
        except Exception:
            pass
    else:
        import winsound as ws
        ws.PlaySound(None, ws.SND_PURGE)
    is_speaking = False