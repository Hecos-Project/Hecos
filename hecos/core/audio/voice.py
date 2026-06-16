"""
MODULE: Voice (TTS) - Hecos
DESCRIPTION: Thin wrapper. Delegates all synthesis to PiperDaemon (piper_daemon.py),
             which keeps the ONNX model loaded in memory after the first call.
"""

from hecos.core.logging import logger
from hecos.core.audio.piper_daemon import get_daemon

is_speaking = False


def speak(text, state=None, _run_id=None, _timeout=0, _start=0):
    global is_speaking
    daemon = get_daemon()
    is_speaking = True
    try:
        daemon.speak(text, state=state, _run_id=_run_id, _timeout=_timeout, _start=_start)
    except Exception as e:
        logger.error("VOICE", f"speak() error: {e}")
    finally:
        is_speaking = False


def stop_voice():
    global is_speaking
    is_speaking = False
    try:
        get_daemon().stop()
    except Exception as e:
        logger.debug("VOICE", f"stop_voice() error: {e}")