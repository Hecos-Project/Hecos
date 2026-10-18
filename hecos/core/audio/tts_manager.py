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
from hecos.core.audio.tts.fish_speech_engine import get_engine as get_fish_speech
from hecos.core.audio.tts_filter import sanitize_text

def _get_engine_instance(engine_name: str) -> BaseTTSEngine:
    if engine_name == "kokoro":
        return get_kokoro()
    elif engine_name == "xtts2":
        return get_xtts()
    elif engine_name in ("fish_speech", "fish"):
        return get_fish_speech()
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


def preload_active_engine(delay: float = 2.0):
    """
    Preloads or starts the background server for the currently configured active TTS engine.
    Non-blocking, safe to call during system or WebUI startup.
    """
    try:
        from hecos.core.audio.device_manager import get_audio_config
        cfg = get_audio_config()
        active = cfg.get("active_engine", "piper")
        if active in ("fish_speech", "fish"):
            from hecos.core.audio.tts.fish_speech_daemon import FishSpeechDaemon
            daemon = FishSpeechDaemon.get_instance()
            if daemon.is_local_target():
                logger.info("TTS_MANAGER", f"Active TTS engine is '{active}': initiating background auto-startup...")
                daemon.preload(delay=delay)
        elif active == "piper":
            from hecos.core.audio.tts.piper_engine import get_engine as get_piper
            piper = get_piper()
            if hasattr(piper, "preload"):
                piper.preload(delay=delay)
    except Exception as e:
        logger.warning("TTS_MANAGER", f"Error during TTS engine preload: {e}")


class TTSManager:
    """
    Facade for all TTS operations.
    """
    @classmethod
    def speak(cls, text: str, state=None, _run_id=None, _timeout=0, _start=0, session_overrides=None):
        text = sanitize_text(text)
        if not text:
            return
        engine = get_engine_for_session(session_overrides)
        try:
            engine.speak(text, state=state, _run_id=_run_id, _timeout=_timeout, _start=_start, session_overrides=session_overrides)
        except Exception as e:
            logger.error("TTS_MANAGER", f"Engine {engine.__class__.__name__} speak error: {e}")
            if not getattr(engine, "_stop_flag", False) and not isinstance(engine, type(get_piper())):
                logger.warning("TTS_MANAGER", "Falling back to Piper.")
                try:
                    get_piper().speak(text, state=state, _run_id=_run_id, _timeout=_timeout, _start=_start, session_overrides=session_overrides)
                except Exception as e2:
                    logger.error("TTS_MANAGER", f"Fallback Piper speak error: {e2}")

    @classmethod
    def generate_wav(cls, text: str, filepath: str, session_overrides=None) -> bool:
        text = sanitize_text(text)
        if not text:
            return False

        # Fast TTSCache lookup
        engine_name = session_overrides.get("tts_engine") if session_overrides else None
        if not engine_name:
            try:
                from hecos.core.audio.device_manager import get_audio_config
                engine_name = get_audio_config().get("active_engine", "piper")
            except Exception:
                engine_name = "piper"

        try:
            from hecos.core.audio.tts_cache import TTSCache
            if TTSCache.get_instance().get_to_file(text, engine=engine_name, out_filepath=filepath, session_overrides=session_overrides):
                return True
        except Exception as _c_err:
            logger.debug("TTS_MANAGER", f"TTSCache check notice: {_c_err}")

        engine = get_engine_for_session(session_overrides)
        try:
            success = engine.generate_wav(text, filepath, session_overrides=session_overrides)
            if not success and not getattr(engine, "_stop_flag", False) and not isinstance(engine, type(get_piper())):
                logger.warning("TTS_MANAGER", "Falling back to Piper.")
                success = get_piper().generate_wav(text, filepath, session_overrides=session_overrides)
                engine_name = "piper"

            if success:
                try:
                    from hecos.core.audio.tts_cache import TTSCache
                    TTSCache.get_instance().put_from_file(text, engine=engine_name, source_filepath=filepath, session_overrides=session_overrides)
                except Exception as _c_put_err:
                    logger.debug("TTS_MANAGER", f"TTSCache put notice: {_c_put_err}")

            return success
        except Exception as e:
            logger.error("TTS_MANAGER", f"Engine {engine.__class__.__name__} generate_wav error: {e}")
            if not getattr(engine, "_stop_flag", False) and not isinstance(engine, type(get_piper())):
                return get_piper().generate_wav(text, filepath, session_overrides=session_overrides)
            return False

    @classmethod
    def generate_wav_chunked(cls, text: str, filepath: str, progress_callback=None, on_chunk_ready=None, session_overrides=None) -> bool:
        engine = get_engine_for_session(session_overrides)
        engine_name = session_overrides.get("tts_engine") if session_overrides else None
        text = sanitize_text(text, engine=engine_name)
        if not text:
            return False

        if not engine_name:
            try:
                from hecos.core.audio.device_manager import get_audio_config
                engine_name = get_audio_config().get("active_engine", "piper")
            except Exception:
                engine_name = "piper"

        # Fast TTSCache lookup
        try:
            from hecos.core.audio.tts_cache import TTSCache
            if TTSCache.get_instance().get_to_file(text, engine=engine_name, out_filepath=filepath, session_overrides=session_overrides):
                if progress_callback:
                    try:
                        progress_callback(1, 1)
                    except TypeError:
                        progress_callback(100)
                if on_chunk_ready:
                    try:
                        with open(filepath, "rb") as _f:
                            _cb = _f.read()
                        on_chunk_ready(0, 1, filepath, _cb)
                    except Exception:
                        pass
                return True
        except Exception as _c_err:
            logger.debug("TTS_MANAGER", f"TTSCache chunked check notice: {_c_err}")

        try:
            try:
                success = engine.generate_wav_chunked(text, filepath, progress_callback, on_chunk_ready=on_chunk_ready, session_overrides=session_overrides)
            except TypeError:
                success = engine.generate_wav_chunked(text, filepath, progress_callback, session_overrides=session_overrides)

            if not success and not getattr(engine, "_stop_flag", False) and not isinstance(engine, type(get_piper())):
                logger.warning("TTS_MANAGER", "Falling back to Piper.")
                try:
                    success = get_piper().generate_wav_chunked(text, filepath, progress_callback, on_chunk_ready=on_chunk_ready, session_overrides=session_overrides)
                except TypeError:
                    success = get_piper().generate_wav_chunked(text, filepath, progress_callback, session_overrides=session_overrides)
                engine_name = "piper"

            if success:
                try:
                    from hecos.core.audio.tts_cache import TTSCache
                    TTSCache.get_instance().put_from_file(text, engine=engine_name, source_filepath=filepath, session_overrides=session_overrides)
                except Exception as _c_put_err:
                    logger.debug("TTS_MANAGER", f"TTSCache put notice: {_c_put_err}")

            return success
        except Exception as e:
            logger.error("TTS_MANAGER", f"Engine {engine.__class__.__name__} chunked error: {e}")
            if not getattr(engine, "_stop_flag", False) and not isinstance(engine, type(get_piper())):
                try:
                    return get_piper().generate_wav_chunked(text, filepath, progress_callback, on_chunk_ready=on_chunk_ready, session_overrides=session_overrides)
                except TypeError:
                    return get_piper().generate_wav_chunked(text, filepath, progress_callback, session_overrides=session_overrides)
            return False

    @classmethod
    def stop(cls):
        """Stop all engines just to be safe."""
        get_piper().stop()
        get_kokoro().stop()
        get_xtts().stop()
        get_fish_speech().stop()

    @classmethod
    def get_available_voices(cls, engine_name: str) -> dict:
        return _get_engine_instance(engine_name).get_available_voices()
