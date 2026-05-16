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
_chat_log = logging.getLogger("HecosChatRoutes")

_CAMERA_TOKEN = "[CAMERA_SNAPSHOT_REQUEST]"


def _run_inference(session_id: str, user_message: str, history: list, cfg_mgr, images=None, user_id="admin"):
    sess = _sessions.get(session_id)
    if not sess:
        return

    try:
        from hecos.core.llm import brain  # noqa: F401 – ensure core is importable
    except ImportError as e:
        sess["queue"].put({"type": "error", "text": f"Core non importabile: {e}"})
        sess["done"] = True
        return

    try:
        from hecos.core.agent.loop import AgentExecutor
        from hecos.modules.web_ui.server import get_state_manager

        sm = get_state_manager()

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
        )

        # ── SSE Connection Buffer ────────────────────────────────────────────
        # Allow the browser to open the SSE stream BEFORE first tokens arrive.
        time.sleep(0.4)
        # ────────────────────────────────────────────────────────────────────

        full_text, clean_voice = agent.run_agentic_loop(user_message, voice_status=True, images=images)

        # ── Client Camera Interceptor ────────────────────────────────────────
        camera_request_pending = _CAMERA_TOKEN in (full_text or "")
        if camera_request_pending:
            full_text = full_text.replace(_CAMERA_TOKEN, "").strip()
        # ────────────────────────────────────────────────────────────────────

        for i in range(0, len(full_text), 40):
            sess["queue"].put({"type": "token", "text": full_text[i:i+40]})
            time.sleep(0.02)

        # Signal the frontend to stop the ⚙️ spinner (before blocking TTS)
        sess["queue"].put({"type": "trace_done"})

        if camera_request_pending:
            sess["queue"].put({"type": "camera_request"})

        sess["history"].append({"role": "user",      "content": user_message})
        sess["history"].append({"role": "assistant",  "content": full_text})

        audio_status = _maybe_generate_tts(clean_voice, cfg_mgr)
        if audio_status == "web":
            sess["queue"].put({"type": "audio_ready",          "text": ""})
        elif audio_status == "system":
            sess["queue"].put({"type": "system_audio_playing", "text": ""})

        sess["queue"].put({"type": "done", "text": ""})

    except Exception as exc:
        _chat_log.error(f"[Chat] Inference error: {exc}")
        sess["queue"].put({"type": "error", "text": str(exc)})
    finally:
        sess["done"] = True
