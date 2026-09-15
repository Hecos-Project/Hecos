"""
MODULE: Voice (TTS) - Hecos
DESCRIPTION: Thin wrapper. Delegates all synthesis to TTSManager,
             which handles routing to the correct TTS engine.
"""

from hecos.core.logging import logger
from hecos.core.audio.tts_manager import TTSManager

is_speaking = False


def speak(text, state=None, _run_id=None, _timeout=0, _start=0, session_overrides=None):
    global is_speaking
    is_speaking = True
    try:
        TTSManager.speak(text, state=state, _run_id=_run_id, _timeout=_timeout, _start=_start, session_overrides=session_overrides)
    except Exception as e:
        logger.error("VOICE", f"speak() error: {e}")
    finally:
        is_speaking = False


def stop_voice():
    global is_speaking
    is_speaking = False
    try:
        TTSManager.stop()
    except Exception as e:
        logger.debug("VOICE", f"stop_voice() error: {e}")