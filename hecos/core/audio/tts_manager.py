"""
MODULE: TTS Manager
DESCRIPTION: Orchestrates TTS requests, resolving the correct engine based on
             system config and session overrides. Handles fallback to Piper.
"""

from hecos.core.logging import logger
from hecos.core.audio.tts.base_engine import BaseTTSEngine
from hecos.core.audio.tts.piper_engine import get_engine as get_piper
from hecos.core.audio.tts.kokoro_engine import get_engine as get_kokoro
from hecos.core.audio.tts.xtts_engine import get_engine as get_xtts

def _get_engine_instance(engine_name: str) -> BaseTTSEngine:
    if engine_name == "kokoro":
        return get_kokoro()
    elif engine_name == "xtts2":
        return get_xtts()
    # Default to piper
    return get_piper()

def get_engine_for_session(session_overrides: dict = None) -> BaseTTSEngine:
    """
    Returns the appropriate engine instance based on session overrides,
    falling back to global config if no override is present.
    """
    try:
        from hecos.core.audio.device_manager import get_audio_config
        global_cfg = get_audio_config()
        active_engine = global_cfg.get("active_engine", "piper")
    except Exception:
        active_engine = "piper"

    if session_overrides and session_overrides.get("tts_engine"):
        override_engine = session_overrides.get("tts_engine")
        if override_engine != "default":
            active_engine = override_engine

    return _get_engine_instance(active_engine)


class TTSManager:
    """
    Facade for all TTS operations.
    """
    @classmethod
    def speak(cls, text: str, state=None, _run_id=None, _timeout=0, _start=0, session_overrides=None):
        engine = get_engine_for_session(session_overrides)
        try:
            engine.speak(text, state=state, _run_id=_run_id, _timeout=_timeout, _start=_start, session_overrides=session_overrides)
        except Exception as e:
            logger.error("TTS_MANAGER", f"Engine {engine.__class__.__name__} speak error: {e}")
            if not isinstance(engine, type(get_piper())):
                logger.warning("TTS_MANAGER", "Falling back to Piper.")
                try:
                    get_piper().speak(text, state=state, _run_id=_run_id, _timeout=_timeout, _start=_start, session_overrides=session_overrides)
                except Exception as e2:
                    logger.error("TTS_MANAGER", f"Fallback Piper speak error: {e2}")

    @classmethod
    def generate_wav(cls, text: str, filepath: str, session_overrides=None) -> bool:
        engine = get_engine_for_session(session_overrides)
        try:
            success = engine.generate_wav(text, filepath, session_overrides=session_overrides)
            if not success and not isinstance(engine, type(get_piper())):
                logger.warning("TTS_MANAGER", "Falling back to Piper.")
                return get_piper().generate_wav(text, filepath, session_overrides=session_overrides)
            return success
        except Exception as e:
            logger.error("TTS_MANAGER", f"Engine {engine.__class__.__name__} generate_wav error: {e}")
            if not isinstance(engine, type(get_piper())):
                return get_piper().generate_wav(text, filepath, session_overrides=session_overrides)
            return False

    @classmethod
    def generate_wav_chunked(cls, text: str, filepath: str, progress_callback=None, session_overrides=None) -> bool:
        engine = get_engine_for_session(session_overrides)
        try:
            success = engine.generate_wav_chunked(text, filepath, progress_callback, session_overrides=session_overrides)
            if not success and not isinstance(engine, type(get_piper())):
                logger.warning("TTS_MANAGER", "Falling back to Piper.")
                return get_piper().generate_wav_chunked(text, filepath, progress_callback, session_overrides=session_overrides)
            return success
        except Exception as e:
            logger.error("TTS_MANAGER", f"Engine {engine.__class__.__name__} chunked error: {e}")
            if not isinstance(engine, type(get_piper())):
                return get_piper().generate_wav_chunked(text, filepath, progress_callback, session_overrides=session_overrides)
            return False

    @classmethod
    def stop(cls):
        """Stop all engines just to be safe."""
        get_piper().stop()
        get_kokoro().stop()
        get_xtts().stop()

    @classmethod
    def get_available_voices(cls, engine_name: str) -> dict:
        return _get_engine_instance(engine_name).get_available_voices()
