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
from hecos.modules.web_ui.routes_chat_tts import get_last_audio_path, get_audio_history_path
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
        urole = current_user.role if current_user.is_authenticated else "admin"
        
        # Save to input history
        try:
            from hecos.modules.input_history import history_mgr
            history_mgr.push(user_msg, user=uid)
        except Exception as e:
            _chat_log.warning(f"[Chat] Failed to push input history: {e}")

        # ── Flow input intercept ───────────────────────────────────────────────
        # If any flow is paused waiting for user input, route this message there
        # before running normal AI inference.
        try:
            from hecos.modules.flows.engine import (
                get_all_pending_input_runs, deliver_user_input, _PENDING_INPUTS, _PENDING_INPUTS_LOCK
            )
            with _PENDING_INPUTS_LOCK:
                pending = list(_PENDING_INPUTS.items())  # [(run_id, entry), ...]

            if pending:
                # Determine intercept_mode from the node params baked into the entry
                # We store it when registering — check each entry
                reply_text = user_msg

                # Parse @flow prefix for explicit mode check
                explicit_text = None
                if user_msg.lower().startswith("@flow "):
                    explicit_text = user_msg[6:].strip()

                delivered = False
                # Respect multi_run_priority stored in entry (default: "first")
                for run_id, entry in pending:
                    mode = entry.get("intercept_mode", "auto")
                    priority = entry.get("multi_run_priority", "first")

                    if mode == "api_only":
                        continue  # Don't intercept from chat

                    if mode == "explicit":
                        if explicit_text is None:
                            continue  # Message doesn't have @flow prefix
                        deliver_user_input(run_id, explicit_text)
                        delivered = True
                    else:  # "auto"
                        deliver_user_input(run_id, reply_text)
                        delivered = True

                    if priority == "first":
                        break  # Only answer the first waiting run

                if delivered:
                    return jsonify({"ok": True, "intercepted": True, "session_id": None})
        except Exception as _ie:
            _chat_log.warning(f"[Chat] Flow intercept check failed: {_ie}")
        # ── End flow intercept ────────────────────────────────────────────────

        sm = get_state_manager()
        if sm:
            sm.webui_stop_requested = False  # Clear any stale cancellation flag

        sid  = data.get("session_id") or privacy_manager.get_session_id() or str(uuid.uuid4())
        tab_id = data.get("tab_id")
        sess = {"queue": queue.Queue(), "history": list(history), "done": False, "user_id": uid}
        with _sessions_lock:
            _sessions[sid] = sess

        threading.Thread(
            target=_run_inference,
            args=(sess, sid, user_msg, history, cfg_mgr, images, uid, urole, tab_id),
            daemon=True,
        ).start()
        return jsonify({"ok": True, "session_id": sid})

    @app.route("/api/chat/session/config", methods=["GET", "POST"])
    def api_session_config():
        from hecos.memory.session_config_db import get_session_config, set_session_config
        
        session_id = request.args.get("session_id")
        if not session_id and request.method == "POST":
            data = request.get_json(force=True) or {}
            session_id = data.get("session_id")
            
        if not session_id:
            return jsonify({"ok": False, "error": "Missing session_id"}), 400
            
        if request.method == "GET":
            conf = get_session_config(session_id)
            return jsonify({"ok": True, "config": conf})
            
        if request.method == "POST":
            data = request.get_json(force=True) or {}
            overrides = data.get("config", {})
            set_session_config(session_id, overrides)
            return jsonify({"ok": True})
            
    @app.route("/api/chat/options")
    def api_chat_options():
        from hecos.core.llm.hybrid_model_manager import get_hybrid_models
        
        # Personas: reuse the config_manager's sync which scans the filesystem
        personas = []
        try:
            personas = cfg_mgr.sync_available_personalities()
        except Exception as e:
            logger.warning(f"[chat/options] Failed to load personas: {e}")
        
        models = get_hybrid_models(cfg_mgr.config, config_manager=cfg_mgr)
        return jsonify({"ok": True, "models": models, "personas": personas})

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
        out = []
        for row in hist:
            role, msg = row[0], row[1]
            persona = row[2] if len(row) > 2 else None
            m_info = row[3] if len(row) > 3 else None
            out.append({"role": role, "content": msg, "persona_name": persona, "model_info": m_info})
        return jsonify(out)

    @app.route("/api/audio")
    def api_audio():
        # Serve a specific history audio by UUID
        audio_id = request.args.get("id", "").strip()
        if audio_id:
            path = get_audio_history_path(audio_id)
            if path:
                _chat_log.debug(f"[Audio] GET /api/audio?id={audio_id} → {path}")
                return send_file(path, mimetype="audio/wav", download_name=f"{audio_id}.wav")
            _chat_log.warning(f"[Audio] GET /api/audio?id={audio_id} — file not found in history.")
            return jsonify({"error": "Audio file not found in history"}), 404

        # Fallback: last generated audio (current session)
        path = get_last_audio_path()
        _chat_log.debug(f"[Audio] GET /api/audio requested. Last path: {path}")
        if path and os.path.exists(path):
            return send_file(path, mimetype="audio/wav", download_name="hecos_response.wav")
        _chat_log.warning(f"[Audio] GET /api/audio failed. Path not found or empty: {path}")
        return jsonify({"error": "No audio available"}), 404

