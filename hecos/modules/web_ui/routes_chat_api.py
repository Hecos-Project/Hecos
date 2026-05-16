"""
routes_chat_api.py
────────────────────────────────────────────────────────────────────────────
Hecos WebUI — Core Chat API Routes
Registers:
  GET  /                     → redirect to /chat
  GET  /chat                 → Chat UI (chat.html)
  POST /api/chat             → start inference session, return session_id
  GET  /api/stream/<sid>     → SSE stream of tokens
  GET  /api/history          → session message history
  GET  /api/audio            → last TTS WAV for browser playback
────────────────────────────────────────────────────────────────────────────
"""
import json
import uuid
import queue
import threading
import logging
from flask import jsonify, request, Response, stream_with_context, render_template, redirect, make_response, send_file

from hecos.modules.web_ui.routes_chat_inference import _sessions, _sessions_lock, _run_inference
from hecos.modules.web_ui.routes_chat_tts import get_last_audio_path
import os

_chat_log = logging.getLogger("HecosChatRoutes")


def init_chat_api_routes(app, cfg_mgr, logger):

    @app.route("/")
    def root_redirect():
        return redirect("/chat")

    @app.route("/chat")
    def chat_ui():
        from flask_login import current_user
        from hecos.core.auth.auth_manager import auth_mgr
        from hecos.core.i18n.translator import get_translator
        from hecos.core.system.extension_loader import get_sidebar_widgets
        try:
            profile      = auth_mgr.get_profile(current_user.username) if current_user.is_authenticated else None
            translations = get_translator().get_translations()
            resp = make_response(render_template(
                "chat.html",
                profile=profile,
                zconfig=cfg_mgr.config,
                translations=translations,
                sidebar_widgets=get_sidebar_widgets(config=cfg_mgr.config),
            ))
            resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            resp.headers["Pragma"] = "no-cache"
            return resp
        except Exception as e:
            return f"<h1>chat.html non trovato</h1><p>{e}</p>", 500

    @app.route("/api/chat", methods=["POST"])
    def api_chat():
        from flask_login import current_user
        from hecos.core.privacy import privacy_manager
        from hecos.modules.web_ui.server import get_state_manager

        data     = request.get_json(force=True) or {}
        user_msg = data.get("message", "").strip()
        history  = data.get("history", [])
        images   = data.get("images", [])

        if not user_msg and not images:
            return jsonify({"ok": False, "error": "Empty message"}), 400

        uid = current_user.username if current_user.is_authenticated else "admin"

        sm = get_state_manager()
        if sm:
            sm.webui_stop_requested = False  # Clear any stale cancellation flag

        sid  = data.get("session_id") or privacy_manager.get_session_id() or str(uuid.uuid4())
        sess = {"queue": queue.Queue(), "history": list(history), "done": False, "user_id": uid}
        with _sessions_lock:
            _sessions[sid] = sess

        threading.Thread(
            target=_run_inference,
            args=(sid, user_msg, history, cfg_mgr, images, uid),
            daemon=True,
        ).start()
        return jsonify({"ok": True, "session_id": sid})

    @app.route("/api/stream/<session_id>")
    def api_stream(session_id):
        sess = _sessions.get(session_id)
        if not sess:
            def err():
                yield "data: " + json.dumps({"type": "error", "text": "Session not found"}) + "\n\n"
            return Response(stream_with_context(err()), mimetype="text/event-stream")

        def generate():
            from hecos.modules.web_ui.server import get_state_manager
            sm = get_state_manager()
            while True:
                # ESC / stop interceptor
                if sm and getattr(sm, "webui_stop_requested", False):
                    sm.webui_stop_requested = False
                    yield "data: " + json.dumps({"type": "error", "text": "⛔ Elaborazione annullata."}) + "\n\n"
                    break
                try:
                    ev = sess["queue"].get(timeout=0.5)
                    yield "data: " + json.dumps(ev) + "\n\n"
                    if ev.get("type") == "error":
                        break
                except queue.Empty:
                    if sess.get("done") and sess["queue"].empty():
                        break
                    yield "data: " + json.dumps({"type": "heartbeat"}) + "\n\n"

            with _sessions_lock:
                _sessions.pop(session_id, None)

        return Response(
            stream_with_context(generate()),
            mimetype="text/event-stream",
            headers={
                "Cache-Control":               "no-cache",
                "X-Accel-Buffering":           "no",
                "Access-Control-Allow-Origin": "*",
            },
        )

    @app.route("/api/history")
    def api_history():
        from flask_login import current_user
        from hecos.memory.brain_interface import get_history
        from hecos.core.privacy import privacy_manager

        uid  = current_user.username if current_user.is_authenticated else "admin"
        sid  = privacy_manager.get_session_id()
        hist = get_history(user_id=uid, session_id=sid)
        return jsonify([{"role": role, "content": msg} for role, msg in hist])

    @app.route("/api/audio")
    def api_audio():
        path = get_last_audio_path()
        _chat_log.debug(f"[Audio] GET /api/audio requested. Last path: {path}")
        if path and os.path.exists(path):
            return send_file(path, mimetype="audio/wav", download_name="hecos_response.wav")
        _chat_log.warning(f"[Audio] GET /api/audio failed. Path not found or empty: {path}")
        return jsonify({"error": "No audio available"}), 404
