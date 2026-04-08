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


# Global persistent recognizer to maintain threshold learning
_recognizer = sr.Recognizer()
_recognizer.dynamic_energy_threshold = True
_recognizer.energy_threshold = 450
_is_calibrated = False


def _get_mic_device_index():
    """Returns the microphone device index from config_audio.json, or None for system default."""
    try:
        from core.audio.device_manager import get_input_device
        return get_input_device()
    except Exception:
        return None


def listen(state=None):
    global _is_calibrated, _recognizer

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

    # Update recognizer settings from config if needed
    _recognizer.energy_threshold = conf.get("energy_threshold", 450)

    # Open Microphone with explicit device index if available
    mic_kwargs = {}
    if device_index is not None:
        mic_kwargs["device_index"] = device_index

    try:
        with sr.Microphone(**mic_kwargs) as source:
            # Calibrate once per session or on first run
            if not _is_calibrated:
                logger.debug("LISTEN", "First run: calibrating for ambient noise (0.5s)...")
                _recognizer.adjust_for_ambient_noise(source, duration=0.5)
                _is_calibrated = True

            # Small delay to avoid hearing the echo of the system's own voice
            if (state and state.system_speaking) or voice.is_speaking:
                return ""

            is_ptt = state.push_to_talk if state else conf.get("push_to_talk", False)

            if not is_ptt or not keyboard:
                # Continuous listening mode: NO repetitive calibration here
                logger.debug("LISTEN", f"Continuous listening active (Threshold: {int(_recognizer.energy_threshold)})...")
                try:
                    audio = _recognizer.listen(
                        source,
                        timeout=conf.get("silence_timeout", 5),
                        phrase_time_limit=conf.get("phrase_limit", 15)
                    )
                    logger.debug("LISTEN", "Phrase captured. Processing...")
                except sr.WaitTimeoutError:
                    return ""
            else:
                hotkey = state.ptt_hotkey if state else conf.get("ptt_hotkey", "ctrl+shift")
                # Push-To-Talk mode: wait for hotkey press
                while not keyboard.is_pressed(hotkey):
                    time.sleep(0.05)
                    if (state and state.system_speaking) or voice.is_speaking:
                        return ""
                    if state and (not state.listening_status or not state.push_to_talk):
                        return ""

                # Signal PTT START to WebUI
                if state:
                    state.add_event("ptt_status", {"active": True})

                logger.info("VOICE", f"[PTT] Recording... Hold '{hotkey}'")

                audio_data = bytearray()
                while keyboard.is_pressed(hotkey):
                    try:
                        buffer = source.stream.read(source.CHUNK)
                        audio_data.extend(buffer)
                    except Exception as e:
                        logger.error(f"[LISTEN] Error: {e}")
                        # Signal PTT END on error too
                        if state:
                            state.add_event("ptt_status", {"active": False})
                        return ""
                    if state and not state.listening_status:
                        break

                # Signal PTT END to WebUI
                if state:
                    state.add_event("ptt_status", {"active": False})

                if len(audio_data) < 4000:  # Too short to be a phrase
                    logger.info("VOICE", "[PTT] Transcription cancelled: audio too short.")
                    return ""

                logger.info("VOICE", "[PTT] Transcribing audio with Whisper...")
                audio = sr.AudioData(bytes(audio_data), source.SAMPLE_RATE, source.SAMPLE_WIDTH)

            # If system started speaking WHILE listening, discard everything
            if (state and state.system_speaking) or voice.is_speaking:
                return ""

            text = _recognizer.recognize_google(audio, language="it-IT", show_all=False)
            return text.lower()

    except Exception as e:
        if "device" not in str(e).lower():
            logger.error(f"[LISTEN] Recognition error: {e}")
        return ""