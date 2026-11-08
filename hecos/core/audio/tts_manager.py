"""
MODULE: TTS Manager
DESCRIPTION: Orchestrates TTS requests, resolving the correct engine based on
             system config and session overrides. Handles fallback to Piper.
"""

import atexit
import gc
import threading
import time
from typing import Tuple

from hecos.core.logging import logger
from hecos.core.audio.tts.base_engine import BaseTTSEngine
from hecos.core.audio.tts.piper_engine import get_engine as get_piper
from hecos.core.audio.tts.kokoro_engine import get_engine as get_kokoro
from hecos.core.audio.tts.xtts_engine import get_engine as get_xtts
from hecos.core.audio.tts.fish_speech_engine import get_engine as get_fish_speech
from hecos.core.audio.tts.process_registry import reap_orphan_tts_processes
from hecos.core.audio.tts_filter import sanitize_text

_boot_preload_lock = threading.Lock()
_boot_preload_started = False
_lifecycle_op_lock = threading.Lock()
_shutdown_lock = threading.Lock()

ENGINE_LABELS = {
    "piper": "Piper TTS",
    "kokoro": "Kokoro-82M",
    "xtts2": "Coqui XTTSv2",
    "fish_speech": "Fish Speech S2",
}


def normalize_engine_name(name: str) -> str:
    n = (name or "piper").strip().lower()
    if n == "fish":
        return "fish_speech"
    if n == "xtts":
        return "xtts2"
    return n

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


def _is_engine_autostart_enabled(engine_name: str, cfg: dict) -> bool:
    eng = normalize_engine_name(engine_name)
    if eng == "piper":
        return bool(cfg.get("piper_autostart", True))
    if eng == "kokoro":
        return bool(cfg.get("kokoro", {}).get("autostart", True))
    if eng == "xtts2":
        return bool(cfg.get("xtts", {}).get("autostart", True))
    if eng == "fish_speech":
        return bool(cfg.get("fish_speech", {}).get("autostart", True))
    return False


def preload_configured_engines(delay: float = 2.0, force: bool = False):
    """
    Single-entry boot orchestrator for TTS daemons and in-memory models.
    - Reaps any stale orphan TTS processes from an unclean exit.
    - Preloads Piper if `piper_autostart` is True (lightweight fallback).
    - Preloads ONLY the currently selected `active_engine` if it is a heavy engine
      (Kokoro, XTTSv2, or Fish Speech) and its `autostart` flag is True.
    - Never loads multiple heavy engines simultaneously at boot.
    """
    global _boot_preload_started
    with _boot_preload_lock:
        if _boot_preload_started and not force:
            logger.debug("TTS_MANAGER", "Boot TTS preload already scheduled in this process — skipping duplicate call.")
            return
        _boot_preload_started = True

    def _boot_worker():
        try:
            reap_orphan_tts_processes(force_all=False)
            if delay > 0:
                time.sleep(delay)

            with _lifecycle_op_lock:
                from hecos.core.audio.device_manager import get_audio_config
                cfg = get_audio_config()
                active = normalize_engine_name(cfg.get("active_engine", "piper"))

                # 1. Lightweight Piper daemon (fallback / primary if active)
                if _is_engine_autostart_enabled("piper", cfg):
                    logger.info("TTS_MANAGER", "Boot preload: starting Piper IPC daemon (lightweight fallback)...")
                    get_piper().preload(delay=0.0, blocking=True)
                else:
                    logger.info("TTS_MANAGER", "Boot preload: Piper auto-start is disabled by config.")

                # 2. Active heavy engine ONLY (never load multiple heavy models together)
                if active in ("kokoro", "xtts2", "fish_speech"):
                    if _is_engine_autostart_enabled(active, cfg):
                        logger.info("TTS_MANAGER", f"Boot preload: loading active TTS engine '{active}'...")
                        if active == "kokoro":
                            get_kokoro().preload(delay=0.0, blocking=True)
                        elif active == "xtts2":
                            get_xtts().preload(delay=0.0, blocking=True, force_download=False)
                        elif active == "fish_speech":
                            get_fish_speech().preload(delay=0.0, blocking=True)
                    else:
                        logger.info("TTS_MANAGER", f"Boot preload: active engine '{active}' has auto-start disabled.")
        except Exception as e:
            logger.warning("TTS_MANAGER", f"Error during boot TTS preload sequence: {e}")

    threading.Thread(target=_boot_worker, daemon=True, name="TTSBootOrchestrator").start()


def preload_active_engine(delay: float = 2.0):
    """Backward-compatible alias for preload_configured_engines."""
    preload_configured_engines(delay=delay, force=False)


def handle_active_engine_switch(prev_engine: str, new_engine: str, cfg: dict = None):
    """
    Handles runtime switching of `active_engine` from Voice Settings:
    - Unloads the previous heavy engine (Kokoro / XTTSv2 / Fish Speech) to free RAM/VRAM.
    - Preloads the newly selected engine if its `autostart` flag is enabled.
    """
    prev_norm = normalize_engine_name(prev_engine)
    new_norm = normalize_engine_name(new_engine)

    def _switch_worker():
        with _lifecycle_op_lock:
            try:
                local_cfg = cfg
                if local_cfg is None:
                    from hecos.core.audio.device_manager import get_audio_config
                    local_cfg = get_audio_config()

                if prev_norm != new_norm and prev_norm in ("kokoro", "xtts2", "fish_speech"):
                    logger.info("TTS_MANAGER", f"Active engine switched '{prev_norm}' -> '{new_norm}': unloading '{prev_norm}'...")
                    _get_engine_instance(prev_norm).unload()

                if _is_engine_autostart_enabled(new_norm, local_cfg):
                    eng = _get_engine_instance(new_norm)
                    if not eng.is_loaded():
                        logger.info("TTS_MANAGER", f"Preloading newly selected active engine '{new_norm}'...")
                        if new_norm == "xtts2":
                            eng.preload(delay=0.1, blocking=True, force_download=False)
                        else:
                            eng.preload(delay=0.1, blocking=True)
            except Exception as e:
                logger.warning("TTS_MANAGER", f"Engine switch lifecycle notice: {e}")

    threading.Thread(target=_switch_worker, daemon=True, name="TTSEngineSwitchWorker").start()


def shutdown_all_tts():
    """
    Cleanly stops all TTS playback, unloads in-memory models, terminates child daemons
    (Piper IPC & Fish Speech FastAPI), and reaps any registered orphan processes.
    Safe to call from atexit, console close handlers, and os._exit(42) reboot hooks.
    """
    if not _shutdown_lock.acquire(blocking=False):
        return
    try:
        from hecos.core.audio.tts import piper_engine, kokoro_engine, xtts_engine, fish_speech_daemon

        if getattr(piper_engine, "_engine_instance", None) is not None:
            try:
                piper_engine._engine_instance.unload()
            except Exception:
                pass

        if getattr(kokoro_engine, "_engine_instance", None) is not None:
            try:
                kokoro_engine._engine_instance.unload()
            except Exception:
                pass

        if getattr(xtts_engine, "_engine_instance", None) is not None:
            try:
                xtts_engine._engine_instance.unload()
            except Exception:
                pass

        if getattr(fish_speech_daemon.FishSpeechDaemon, "_instance", None) is not None:
            try:
                fish_speech_daemon.FishSpeechDaemon._instance.stop(force_all=False)
            except Exception:
                pass

        reap_orphan_tts_processes(force_all=False, include_own=True)
    except Exception as e:
        logger.debug("TTS_MANAGER", f"shutdown_all_tts notice: {e}")
    finally:
        _shutdown_lock.release()


atexit.register(shutdown_all_tts)


def get_all_engines_status() -> dict:
    """Returns live runtime diagnostics and config flags for all 4 TTS engines."""
    try:
        from hecos.core.audio.device_manager import get_audio_config
        cfg = get_audio_config()
    except Exception:
        cfg = {}

    active = normalize_engine_name(cfg.get("active_engine", "piper"))
    engines_out = {}
    for key in ("piper", "kokoro", "xtts2", "fish_speech"):
        try:
            inst = _get_engine_instance(key)
            st = inst.get_runtime_status()
        except Exception as e:
            st = {
                "status": "offline",
                "loaded": False,
                "installed": False,
                "mode": "daemon" if key in ("piper", "fish_speech") else "in-process",
                "pid": None,
                "ram_mb": 0.0,
                "vram_mb": 0.0,
                "last_error": str(e),
            }
        st["engine"] = key
        st["label"] = ENGINE_LABELS.get(key, key)
        st["active"] = (active == key)
        st["fallback"] = (key == "piper")
        st["autostart"] = _is_engine_autostart_enabled(key, cfg)
        engines_out[key] = st

    return {
        "ok": True,
        "active_engine": active,
        "engines": engines_out,
    }


def perform_engine_action(engine_name: str, action: str) -> Tuple[bool, str]:
    """
    Executes a runtime lifecycle action ('start'|'load', 'stop'|'unload', 'restart')
    on a specific TTS engine or 'all' (for stop/unload).
    """
    act = (action or "").strip().lower()
    if act == "load":
        act = "start"
    elif act == "unload":
        act = "stop"

    if act not in ("start", "stop", "restart"):
        return False, f"Unsupported action '{action}'."

    if (engine_name or "").strip().lower() == "all":
        if act != "stop":
            return False, "Action 'all' only supports 'stop' / 'unload'."
        for key in ("piper", "kokoro", "xtts2", "fish_speech"):
            try:
                _get_engine_instance(key).unload()
            except Exception as e:
                logger.warning("TTS_MANAGER", f"Stop-all notice for {key}: {e}")
        reap_orphan_tts_processes(force_all=True)
        gc.collect()
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass
        return True, "All TTS daemons stopped and RAM/VRAM freed."

    eng_key = normalize_engine_name(engine_name)
    if eng_key not in ENGINE_LABELS:
        return False, f"Unknown TTS engine '{engine_name}'."

    label = ENGINE_LABELS[eng_key]
    inst = _get_engine_instance(eng_key)

    if act == "stop":
        ok = inst.unload()
        return ok, (f"{label} stopped and memory freed." if ok else f"Failed to stop {label}.")

    if act == "restart":
        inst.unload()
        time.sleep(0.4)

    # Start / Load path
    if eng_key == "piper":
        inst.preload(delay=0.0, blocking=True)
        if inst.is_loaded():
            return True, f"{label} IPC daemon is online."
        st = inst.get_runtime_status()
        if not st.get("installed"):
            return False, "Piper executable or ONNX model not found at configured paths."
        return False, f"{label} daemon failed to start."

    if eng_key == "kokoro":
        if not inst.is_available():
            return False, "Kokoro Python package is not installed."
        res = inst.preload(delay=0.0, blocking=False)
        if isinstance(res, threading.Thread):
            res.join(timeout=1.5)
        if inst.is_loaded():
            return True, f"{label} model loaded and ready."
        return True, f"{label} model loading in background..."

    if eng_key == "xtts2":
        if not inst.is_available():
            return False, "Coqui TTS (XTTSv2) package is not installed."
        if not inst.model_ready():
            return False, "XTTSv2 weights (~1.8 GB) are not downloaded on disk yet."
        res = inst.preload(delay=0.0, blocking=False, force_download=False)
        if isinstance(res, threading.Thread):
            res.join(timeout=1.5)
        if inst.is_loaded():
            return True, f"{label} model loaded and ready."
        return True, f"{label} model loading in background..."

    if eng_key == "fish_speech":
        from hecos.core.audio.tts.fish_speech_daemon import FishSpeechDaemon
        daemon = FishSpeechDaemon.get_instance()
        if not daemon.is_local_target():
            return True, "Fish Speech is configured for Cloud API (no local daemon required)."
        ok_pre, pre_msg = daemon.check_preconditions()
        if not ok_pre:
            return False, pre_msg
        t = daemon.preload(delay=0.0)
        if isinstance(t, threading.Thread):
            t.join(timeout=1.5)
        st = daemon.get_runtime_status()
        if st.get("status") == "online":
            return True, f"{label} local server is online on port {st.get('port')}."
        return True, f"{label} local server starting in background on port {st.get('port')}..."

    return False, f"Unhandled engine '{eng_key}'." 


class TTSManager:
    """
    Facade for all TTS operations.
    """
    _last_used_engine: str = "piper"

    @classmethod
    def get_last_used_engine(cls) -> str:
        return getattr(cls, "_last_used_engine", "piper")

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

        cls._last_used_engine = engine_name

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
                cls._last_used_engine = "piper"

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
                cls._last_used_engine = "piper"
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

        cls._last_used_engine = engine_name

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
                cls._last_used_engine = "piper"

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
                cls._last_used_engine = "piper"
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
