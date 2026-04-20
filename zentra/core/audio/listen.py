"""
MODULE: Listen (STT) - Zentra Core
DESCRIPTION: Microphone input and speech recognition.
             Uses the input device selected by device_manager when available.
             PTT state is now managed by ptt_bus — this module only reads it.
"""

import speech_recognition as sr
from . import voice
from zentra.core.logging import logger
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
        from zentra.core.audio.device_manager import get_input_device
        return get_input_device()
    except Exception:
        return None


def listen(state=None):
    global _is_calibrated, _recognizer

    # Redundant check: if system is speaking, don't listen at all
    if (state and state.system_speaking) or voice.is_speaking:
        return ""

    try:
        from zentra.core.audio.device_manager import get_audio_config
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

            if not is_ptt:
                # ── CONTINUOUS LISTENING MODE ─────────────────────────────
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
                # ── PTT MODE ─────────────────────────────────────────────
                # The ptt_bus manages all input sources (keyboard, media keys,
                # webhook, custom key). Here we just read ptt_bus.ptt_active.
                from zentra.core.audio import ptt_bus

                # Wait for PTT to activate (from any source)
                while not ptt_bus.ptt_active:
                    time.sleep(0.03)
                    
                    # DRAIN THE AUDIO STREAM to prevent PyAudio IOError (Input Overflow)
                    # If we don't read while waiting, the OS buffer fills up and crashes on the first read.
                    try:
                        source.stream.read(source.CHUNK, exception_on_overflow=False)
                    except Exception:
                        pass
                        
                    if (state and state.system_speaking) or voice.is_speaking:
                        return ""
                    if state and (not state.listening_status or not state.push_to_talk):
                        return ""

                # Signal PTT START to WebUI
                if state:
                    state.add_event("ptt_status", {"active": True})
                logger.info("VOICE", f"[PTT] Recording... Source: {ptt_bus.get_last_source()}")

                # Capture audio while PTT remains active
                audio_data = bytearray()
                while ptt_bus.ptt_active:
                    try:
                        buffer = source.stream.read(source.CHUNK)
                        audio_data.extend(buffer)
                    except Exception as e:
                        logger.error(f"[LISTEN] Error: {e}")
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

                logger.info("VOICE", "[PTT] Transcribing audio...")
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