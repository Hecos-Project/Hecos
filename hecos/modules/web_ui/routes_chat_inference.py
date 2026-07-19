"""
routes_chat_inference.py
────────────────────────────────────────────────────────────────────────────
Hecos WebUI — Chat Inference Engine
Provides:
  _run_inference()  → background thread that runs the AgentExecutor and pumps
                      tokens into the session SSE queue
  _sessions         → shared dict {sid: {queue, history, done, user_id}}
  _sessions_lock    → threading.Lock for safe session access
────────────────────────────────────────────────────────────────────────────
"""
import time
import threading
import queue
import logging

from hecos.modules.web_ui.routes_chat_tts import _maybe_generate_tts

_sessions      = {}
_sessions_lock = threading.Lock()
from hecos.core.logging import logger as _chat_log

_CAMERA_TOKEN = "[CAMERA_SNAPSHOT_REQUEST]"

# ── Default WebUI inference timeout (seconds) ────────────────────────────────
# Overridden at runtime by /hecos/api/keymanager/settings (webui_timeout field)
_WEBUI_INFERENCE_TIMEOUT = 120  # seconds


def _run_inference(sess: dict, session_id: str, user_message: str, history: list, cfg_mgr, images=None, user_id="admin", user_role="admin", sender_tab_id=None):
    if not sess:
        return

    t_start = time.monotonic()
    _chat_log.info(f"[INFERENCE] ══ START sid={session_id[:8]} user={user_id} msg_len={len(user_message)} images={len(images) if images else 0}")

    try:
        from hecos.core.llm import brain  # noqa: F401 – ensure core is importable
    except ImportError as e:
        _chat_log.error(f"[INFERENCE] Core import failed: {e}")
        sess["queue"].put({"type": "error", "text": f"Core non importabile: {e}"})
        sess["done"] = True
        return

    # ── Watchdog: kills the session if inference takes too long ──────────────
    try:
        import hecos.core.keys.key_manager as _km_mod
        webui_timeout = getattr(_km_mod, "_KM_WEBUI_INFERENCE_TIMEOUT", _WEBUI_INFERENCE_TIMEOUT)
    except Exception:
        webui_timeout = _WEBUI_INFERENCE_TIMEOUT

    _timed_out = threading.Event()

    def _watchdog():
        deadline = time.monotonic() + webui_timeout
        while not _timed_out.is_set():
            if time.monotonic() >= deadline:
                elapsed = time.monotonic() - t_start
                _chat_log.warning(f"[INFERENCE] ⚠️ WATCHDOG TIMEOUT after {elapsed:.1f}s (limit={webui_timeout}s) sid={session_id[:8]}")
                sess["queue"].put({"type": "error", "text": f"⏰ Timeout: nessuna risposta dall'AI entro {webui_timeout}s. Il provider potrebbe essere lento o irraggiungibile."})
                sess["done"] = True
                return
            time.sleep(0.5)

    _wd_thread = threading.Thread(target=_watchdog, daemon=True)
    _wd_thread.start()
    _chat_log.info(f"[INFERENCE] Watchdog started (limit={webui_timeout}s)")
    # ──────────────────────────────────────────────────────────────────────────

    try:
        from hecos.core.agent.loop import AgentExecutor
        from hecos.modules.web_ui.server import get_state_manager

        sm = get_state_manager()

        # ── Defensive cfg_mgr recovery ───────────────────────────────────────
        # If cfg_mgr is None (timing gap between boot paths), try to recover it
        # from the StateManager or from sys before crashing silently.
        if cfg_mgr is None:
            _chat_log.warning("[INFERENCE] cfg_mgr is None — attempting recovery from StateManager/sys...")
            if sm and hasattr(sm, "config_manager") and sm.config_manager is not None:
                cfg_mgr = sm.config_manager
                _chat_log.info("[INFERENCE] cfg_mgr recovered from StateManager.")
            elif sm and hasattr(sm, "_cfg_mgr") and sm._cfg_mgr is not None:
                cfg_mgr = sm._cfg_mgr
                _chat_log.info("[INFERENCE] cfg_mgr recovered from StateManager._cfg_mgr.")
            else:
                import sys as _sys
                cfg_mgr = getattr(_sys, "hecos_config_manager", None)
                if cfg_mgr:
                    _chat_log.info("[INFERENCE] cfg_mgr recovered from sys.hecos_config_manager.")

        if cfg_mgr is None:
            raise RuntimeError("ConfigManager non disponibile. Riavviare Hecos.")
        # ────────────────────────────────────────────────────────────────────

        # ── Session-Aware Trace Callback ─────────────────────────────────────
        # Inject agent traces directly into the session-specific SSE queue.
        def _session_trace(msg: str, level: str = "info"):
            sess["queue"].put({"type": "agent_trace", "level": level, "message": msg})
        # ────────────────────────────────────────────────────────────────────

        agent = AgentExecutor(
            config=cfg_mgr.config,
            config_manager=cfg_mgr,
            state_manager=sm,
            trace_callback=_session_trace,
            current_user_id=user_id,
            current_user_role=user_role,
            session_id=session_id,
            sender_tab_id=sender_tab_id
        )

        # ── SSE Connection Buffer ────────────────────────────────────────────
        # Allow the browser to open the SSE stream BEFORE first tokens arrive.
        time.sleep(0.4)
        # ────────────────────────────────────────────────────────────────────

        _chat_log.info(f"[INFERENCE] Calling AgentExecutor.run_agentic_loop...")
        t_llm_start = time.monotonic()

        full_text, clean_voice = agent.run_agentic_loop(user_message, voice_status=True, images=images)

        t_llm_end = time.monotonic()
        _chat_log.info(f"[INFERENCE] AgentExecutor returned in {t_llm_end - t_llm_start:.2f}s | response_len={len(full_text or '')} chars")

        # Stop watchdog - we got a response
        _timed_out.set()

        # If watchdog already fired (race condition), don't push more tokens
        if sess.get("done"):
            _chat_log.warning(f"[INFERENCE] Watchdog already fired, discarding late LLM response.")
            return

        # ── Client Camera Interceptor ────────────────────────────────────────
        camera_request_pending = _CAMERA_TOKEN in (full_text or "")
        if camera_request_pending:
            full_text = full_text.replace(_CAMERA_TOKEN, "").strip()
        # ────────────────────────────────────────────────────────────────────

        _chat_log.info(f"[INFERENCE] Streaming {len(full_text)} chars to client...")
        for i in range(0, len(full_text), 40):
            sess["queue"].put({"type": "token", "text": full_text[i:i+40]})
            time.sleep(0.02)

        # Signal the frontend to stop the ⚙️ spinner (before blocking TTS)
        sess["queue"].put({"type": "trace_done"})

        if camera_request_pending:
            sess["queue"].put({"type": "camera_request"})

        sess["history"].append({"role": "user",      "content": user_message})
        sess["history"].append({"role": "assistant",  "content": full_text})

        _chat_log.info(f"[INFERENCE] Generating TTS...")
        t_tts_start = time.monotonic()
        audio_status = _maybe_generate_tts(clean_voice, cfg_mgr)
        _chat_log.info(f"[INFERENCE] TTS done in {time.monotonic() - t_tts_start:.2f}s | status={audio_status}")

        if audio_status == "web":
            sess["queue"].put({"type": "audio_ready",          "text": ""})
        elif audio_status == "system":
            sess["queue"].put({"type": "system_audio_playing", "text": ""})

        sess["queue"].put({"type": "done", "text": ""})

    except Exception as exc:
        _timed_out.set()  # stop watchdog
        _chat_log.error(f"[INFERENCE] ❌ Exception after {time.monotonic() - t_start:.2f}s: {exc}", exc_info=True)
        if not sess.get("done"):  # don't push if watchdog already sent error
            sess["queue"].put({"type": "error", "text": str(exc)})
    finally:
        _timed_out.set()  # always stop watchdog
        sess["done"] = True
        _chat_log.info(f"[INFERENCE] ══ END sid={session_id[:8]} total={time.monotonic() - t_start:.2f}s")
