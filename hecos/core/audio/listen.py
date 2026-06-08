"""
MODULE: Listen (STT) - Hecos
DESCRIPTION: Microphone input and speech recognition.
             Uses the input device selected by device_manager when available.
             PTT state is now managed by ptt_bus — this module only reads it.
"""

import speech_recognition as sr
from . import voice
from hecos.core.logging import logger
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
_persistent_source = None


def listen(state=None):
    global _is_calibrated, _recognizer, _persistent_source

    # Redundant check: if system is speaking, don't listen at all
    if (state and state.system_speaking) or voice.is_speaking:
        return ""

    # If the microphone is MUTED from the UI, completely close the audio stream 
    # so the Windows 11 Privacy Icon disappears completely from the taskbar.
    if state and not state.listening_status:
        if _persistent_source is not None:
            try:
                _persistent_source.__exit__(None, None, None)
            except Exception:
                pass
            _persistent_source = None
        return ""

    try:
        from hecos.core.audio.device_manager import get_audio_config
        conf = get_audio_config()
    except Exception:
        conf = {}

    # Update recognizer settings from config if needed
    _recognizer.energy_threshold = conf.get("energy_threshold", 450)

    try:
        if _persistent_source is None:
            logger.warning("[LISTEN-DEBUG] Creating NEW microphone source!")
            _persistent_source = sr.Microphone()
            _persistent_source.__enter__()
        
        source = _persistent_source
        
        # We use a try-finally equivalent by catching exceptions if the source dies
        try:
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
                while True:
                    if (state and state.system_speaking) or voice.is_speaking:
                        return ""
                    if state and (not state.listening_status or state.push_to_talk):
                        return ""
                        
                    try:
                        audio = _recognizer.listen(
                            source,
                            timeout=conf.get("silence_timeout", 5),
                            phrase_time_limit=conf.get("phrase_limit", 15)
                        )
                        logger.debug("LISTEN", "Phrase captured. Processing...")
                        break
                    except sr.WaitTimeoutError:
                        # Instead of returning to threads.py (which sleeps 0.2s and causes Windows to flicker the mic icon),
                        # we immediately loop and listen again, keeping the audio stream constantly fed.
                        continue
            else:
                # ── PTT MODE ─────────────────────────────────────────────
                # The ptt_bus manages all input sources (keyboard, media keys,
                # webhook, custom key). Here we just read ptt_bus.ptt_active.
                from hecos.core.audio import ptt_bus

                # Wait for PTT to activate (from any source)
                while not ptt_bus.ptt_active:
                    # DRAIN THE AUDIO STREAM to prevent PyAudio IOError (Input Overflow)
                    # We rely on stream.read() to block (approx 64ms per CHUNK), inherently throttling the loop.
                    # This prevents Windows 11 from detecting the audio session as "Inactive" which causes flickering.
                    try:
                        source.stream.read(source.CHUNK, exception_on_overflow=False)
                    except Exception:
                        time.sleep(0.01)
                        pass
                        
                    if (state and state.system_speaking) or voice.is_speaking:
                        return ""
                    if state and (not state.listening_status or not state.push_to_talk):
                        return ""

                # Signal PTT START to WebUI (Handled by ptt_bus)
                logger.info("VOICE", f"[PTT] Recording started. Source: {ptt_bus.get_last_source()} | Device: OS Default")

                # Capture audio while PTT remains active
                audio_data = bytearray()
                while ptt_bus.ptt_active:
                    try:
                        buffer = source.stream.read(source.CHUNK)
                        audio_data.extend(buffer)
                    except Exception as e:
                        logger.error(f"[LISTEN] PTT capture error: {e}")
                        return ""
                    if state and not state.listening_status:
                        break
                
                # Keep listening for a short 350ms tail to prevent word truncation on fast release
                if not (state and not state.listening_status):
                    grace_end = time.time() + 0.35
                    while time.time() < grace_end:
                        try:
                            buffer = source.stream.read(source.CHUNK)
                            audio_data.extend(buffer)
                        except Exception:
                            pass

                # Signal PTT END to WebUI (Handled by ptt_bus)

                captured_bytes = len(audio_data)
                logger.info("VOICE", f"[PTT] Capture complete. Bytes: {captured_bytes} | SampleRate: {source.SAMPLE_RATE} | Width: {source.SAMPLE_WIDTH}")

                if captured_bytes < 4000:  # Too short to be a phrase
                    logger.info("VOICE", f"[PTT] Cancelled: audio too short ({captured_bytes} bytes).")
                    return ""

                logger.info("VOICE", "[PTT] Sending to Google STT...")
                audio = sr.AudioData(bytes(audio_data), source.SAMPLE_RATE, source.SAMPLE_WIDTH)

            # If system started speaking WHILE listening, discard everything
            if (state and state.system_speaking) or voice.is_speaking:
                return ""

            try:
                text = _recognizer.recognize_google(audio, language="it-IT", show_all=False)
                logger.info("VOICE", f"[PTT] Transcribed: '{text}'")
                return text.lower()
            except sr.UnknownValueError:
                logger.info("VOICE", "[PTT] Google STT: speech not understood.")
                return ""
                
        except Exception as inner_e:
            # If the stream died (e.g. device disconnected), reset the source
            logger.warning(f"[LISTEN-DEBUG] Destroying mic due to inner exception: {inner_e}")
            _persistent_source.__exit__(None, None, None)
            _persistent_source = None
            raise inner_e

    except Exception as e:
        if "device" not in str(e).lower() and "UnknownValueError" not in str(e):
            logger.error(f"[LISTEN] Recognition error: {e}")
            logger.warning("[LISTEN-DEBUG] Destroying mic due to outer exception!")
            _persistent_source = None
        return ""

