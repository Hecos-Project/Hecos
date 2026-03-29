"""
MODULE: Listen (STT) - Zentra Core
DESCRIPTION: Microphone input and speech recognition.
             Uses the input device selected by device_manager when available.
"""

import speech_recognition as sr
from . import voice
from core.logging import logger
import json
import time

try:
    import keyboard
except ImportError:
    keyboard = None


def _get_mic_device_index():
    """Returns the microphone device index from config_audio.json, or None for system default."""
    try:
        from core.audio.device_manager import get_input_device
        return get_input_device()
    except Exception:
        return None


def listen(state=None):
    # Redundant check: if system is speaking, don't listen at all
    if (state and state.system_speaking) or voice.is_speaking:
        return ""

    try:
        from core.audio.device_manager import get_audio_config
        conf = get_audio_config()
    except Exception:
        conf = {}

    # Resolve microphone device index
    device_index = _get_mic_device_index()

    r = sr.Recognizer()
    r.energy_threshold = conf.get("energy_threshold", 450)
    r.dynamic_energy_threshold = False

    # Open Microphone with explicit device index if available
    mic_kwargs = {}
    if device_index is not None:
        mic_kwargs["device_index"] = device_index

    with sr.Microphone(**mic_kwargs) as source:
        # Small delay to avoid hearing the echo of the system's own voice
        if (state and state.system_speaking) or voice.is_speaking:
            return ""

        try:
            is_ptt = state.push_to_talk if state else conf.get("push_to_talk", False)

            if not is_ptt or not keyboard:
                # Continuous listening mode
                r.adjust_for_ambient_noise(source, duration=0.2)
                audio = r.listen(
                    source,
                    timeout=conf.get("silence_timeout", 5),
                    phrase_time_limit=conf.get("phrase_limit", 15)
                )
            else:
                hotkey = state.ptt_hotkey if state else conf.get("ptt_hotkey", "ctrl+shift")
                # Push-To-Talk mode: wait for hotkey press
                while not keyboard.is_pressed(hotkey):
                    try:
                        source.stream.read(source.CHUNK)
                    except Exception:
                        pass
                    if (state and state.system_speaking) or voice.is_speaking:
                        return ""
                    if state and not state.listening_status:
                        return ""

                logger.info("VOICE", f"[PTT] Recording... Hold '{hotkey}'")

                audio_data = bytearray()
                while keyboard.is_pressed(hotkey):
                    try:
                        buffer = source.stream.read(source.CHUNK)
                        audio_data.extend(buffer)
                    except Exception:
                        pass

                if len(audio_data) < 4000:  # Too short to be a phrase
                    logger.info("VOICE", "[PTT] Transcription cancelled: audio too short.")
                    return ""

                logger.info("VOICE", "[PTT] Transcribing audio with Whisper...")
                audio = sr.AudioData(bytes(audio_data), source.SAMPLE_RATE, source.SAMPLE_WIDTH)

            # If system started speaking WHILE listening, discard everything
            if (state and state.system_speaking) or voice.is_speaking:
                return ""

            text = r.recognize_google(audio, language="it-IT", show_all=False)
            return text.lower()

        except Exception:
            return ""