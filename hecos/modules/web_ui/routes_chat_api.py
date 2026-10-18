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
import time
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

        # ── Direct TTS commands (/speak, /tts, /say, /parla, /voce) ─────────────────
        raw_cmd = user_msg.strip()
        first_token = raw_cmd.split()[0].lower() if raw_cmd else ""
        if first_token in ("/speak", "/tts", "/say", "/parla", "/voce"):
            parts = raw_cmd.split(maxsplit=1)
            text_to_speak = parts[1].strip() if len(parts) > 1 else ""

            sid  = data.get("session_id") or privacy_manager.get_session_id() or str(uuid.uuid4())
            sess = {"queue": queue.Queue(), "history": list(history), "done": False, "user_id": uid}
            with _sessions_lock:
                _sessions[sid] = sess

            def _handle_direct_tts():
                try:
                    if not text_to_speak:
                        msg = (
                            "🗣️ **Direct TTS Command (LLM Bypass)**\n\n"
                            "Usage: `/speak <text to pronounce>` (or `/parla`, `/tts`)\n\n"
                            "*Example:*\n"
                            "`/speak Hello Tony, I am Urania. This is a direct voice test.`"
                        )
                        time.sleep(0.05)
                        sess["queue"].put({"type": "token", "text": msg})
                        sess["queue"].put({"type": "trace_done", "persona_name": "Direct TTS", "model_info": "Usage"})
                        sess["history"].append({"role": "user", "content": user_msg})
                        sess["history"].append({"role": "assistant", "content": msg})
                        sess["queue"].put({"type": "done", "text": ""})
                        sess["done"] = True
                        return

                    bubble_text = f"🗣️ {text_to_speak}"
                    time.sleep(0.05)
                    sess["queue"].put({"type": "token", "text": bubble_text})
                    sess["queue"].put({"type": "trace_done", "persona_name": "Direct TTS", "model_info": "Bypass LLM"})

                    from hecos.config.session_config_manager import merge_session_config
                    from hecos.modules.web_ui.routes_chat_tts import _maybe_generate_tts
                    merged_cfg = merge_session_config(cfg_mgr.config if cfg_mgr else {}, sid)
                    
                    class DirectCfgMgr:
                        def __init__(self, base, cfg):
                            self._base = base
                            self.config = cfg
                        def save_config(self):
                            pass
                        def __getattr__(self, name):
                            return getattr(self._base, name)

                    active_cfg = DirectCfgMgr(cfg_mgr, merged_cfg)

                    def _on_chunk_ready(chunk_idx, total_chunks, *args):
                        pass

                    _chat_log.info(f"[Chat] Direct TTS requested for '{text_to_speak[:50]}'...")
                    audio_status, audio_id = _maybe_generate_tts(text_to_speak, active_cfg, on_chunk_ready=_on_chunk_ready)
                    _chat_log.info(f"[Chat] Direct TTS finished: status={audio_status} audio_id={audio_id}")

                    if audio_status == "web":
                        sess["queue"].put({"type": "audio_ready", "text": "", "audio_id": audio_id or ""})
                        if audio_id:
                            try:
                                from hecos.memory.brain_interface import _db_path
                                uid = sess.get("user_id", "admin")
                                db  = _db_path(uid)
                                import sqlite3
                                with sqlite3.connect(db, timeout=10) as _conn:
                                    _conn.execute(
                                        "UPDATE history SET audio_file = ? WHERE id = ("
                                        "  SELECT MAX(id) FROM history WHERE session_id = ? AND role = 'assistant'"
                                        ")",
                                        (audio_id, sid)
                                    )
                                    _conn.commit()
                            except Exception as _ae:
                                _chat_log.warning(f"[Chat] Direct TTS could not save audio_id to DB: {_ae}")
                    elif audio_status == "system":
                        sess["queue"].put({"type": "system_audio_playing", "text": ""})

                    sess["history"].append({"role": "user", "content": user_msg})
                    sess["history"].append({"role": "assistant", "content": bubble_text})
                    sess["queue"].put({"type": "done", "text": ""})
                    sess["done"] = True
                except Exception as _ex:
                    _chat_log.error(f"[Chat] Direct TTS command error: {_ex}")
                    sess["queue"].put({"type": "error", "text": f"Errore comando TTS: {_ex}"})
                    sess["queue"].put({"type": "done", "text": ""})
                    sess["done"] = True

            threading.Thread(target=_handle_direct_tts, daemon=True).start()
            return jsonify({"ok": True, "session_id": sid})

        # ── Playbook simulation slash commands (/pb ...) ────────────────────
        pb_cmd = user_msg.strip().lower()
        if pb_cmd.startswith("/pb") or pb_cmd.startswith("/playbook"):
            sid  = data.get("session_id") or privacy_manager.get_session_id() or str(uuid.uuid4())
            sess = {"queue": queue.Queue(), "history": list(history), "done": False, "user_id": uid}
            with _sessions_lock:
                _sessions[sid] = sess
            
            def _handle_pb_command():
                try:
                    from hecos.modules.playbooks.playbooks import storage as pb_storage
                    from hecos.modules.web_ui.extensions.presenter.feed import add_feed_entry
                    parts = pb_cmd.split()
                    subcmd = parts[1] if len(parts) > 1 else "status"
                    
                    reply_text = ""
                    if subcmd in ("start", "run", "play"):
                        state = pb_storage.start_simulation(sid)
                        pb = pb_storage.get_playbook(state.get("playbook_id", "")) if state.get("playbook_id") else None
                        if not pb:
                            for p in pb_storage.list_playbooks():
                                if p.get("meta", {}).get("enabled"):
                                    pb = p
                                    state = pb_storage.start_simulation(sid, pb["meta"]["id"])
                                    break
                        if pb:
                            raw_u = m.get("user_role", "User")
                            raw_c = m.get("chat_role", "Interlocutor")
                            coach_role = m.get("coach_role", "Coach")
                            is_swapped = state.get("swapped", False)
                            u_role = raw_c if is_swapped else raw_u
                            c_role = raw_u if is_swapped else raw_c
                            swap_badge = " (⇄ Ruoli Invertiti)" if is_swapped else ""
                            add_feed_entry("playbook_event", f"▶ Simulation STARTED{swap_badge} — User: {u_role} · Chat: {c_role} · Coach: {coach_role}", session_id=sid)
                            reply_text = (
                                f"🎮 **Simulazione Avviata!**\n\n"
                                f"• **Playbook:** {pb.get('meta', {}).get('name', 'Playbook')}\n"
                                f"• **Obiettivo:** {m.get('objective', 'Non specificato')}\n"
                                f"• **Il tuo ruolo:** {u_role}\n"
                                f"• **Ruolo Chat:** {c_role}\n"
                                f"• **Coach (Presenter):** {coach_role}\n\n"
                                f"*La simulazione è attiva. Invia il tuo primo messaggio per iniziare!*"
                            )
                        else:
                            reply_text = "⚠️ Nessun playbook attivo trovato. Attiva un playbook nel pannello Playbooks prima di avviare la simulazione."
                    elif subcmd in ("stop", "end", "quit"):
                        pb_storage.stop_simulation(sid)
                        add_feed_entry("playbook_event", "⏹ Simulation STOPPED — Playbook returned to idle knowledge mode.", session_id=sid)
                        reply_text = "⏹ **Simulazione Terminata.** Il sistema è tornato alla modalità conversazionale standard."
                    elif subcmd in ("pause", "freeze"):
                        pb_storage.pause_simulation(sid)
                        add_feed_entry("playbook_event", "⏸ Simulation PAUSED.", session_id=sid)
                        reply_text = "⏸ **Simulazione in Pausa.** Usa `/pb start` per riprenderla."
                    elif subcmd in ("swap", "invert"):
                        state = pb_storage.swap_roles(sid)
                        pb = pb_storage.get_playbook(state.get("playbook_id", "")) if state.get("playbook_id") else None
                        m = pb.get("mission", {}) if pb else {}
                        u_role = m.get("chat_role", "Chat") if state.get("swapped") else m.get("user_role", "User")
                        c_role = m.get("user_role", "User") if state.get("swapped") else m.get("chat_role", "Chat")
                        add_feed_entry("playbook_event", f"⇄ Roles SWAPPED — User: {u_role} · Chat: {c_role}", session_id=sid)
                        reply_text = f"⇄ **Ruoli Invertiti!**\n\n• **Il tuo nuovo ruolo:** {u_role}\n• **Ruolo Chat:** {c_role}\n\nIl coach si adatta alla nuova prospettiva per guidarti."
                    else: # status
                        state = pb_storage.get_simulation_state(sid)
                        pb = pb_storage.get_playbook(state.get("playbook_id", "")) if state.get("playbook_id") else None
                        pb_name = pb.get("meta", {}).get("name", "Nessuno") if pb else "Nessuno"
                        reply_text = (
                            f"📊 **Stato Simulazione:** {state.get('status', 'idle').upper()}\n"
                            f"• **Playbook:** {pb_name}\n"
                            f"• **Turni eseguiti:** {state.get('turn_count', 0)}\n"
                            f"• **Ruoli invertiti:** {'Sì' if state.get('swapped') else 'No'}\n"
                            f"• **Violazioni registrate:** {len(state.get('violations', []))}\n\n"
                            f"*Comandi disponibili:* `/pb start`, `/pb stop`, `/pb pause`, `/pb swap`, `/pb status`"
                        )
                    
                    time.sleep(0.1)
                    sess["queue"].put({"type": "token", "text": reply_text})
                    sess["queue"].put({"type": "trace_done", "persona_name": "System", "model_info": None})
                    sess["history"].append({"role": "user", "content": user_msg})
                    sess["history"].append({"role": "assistant", "content": reply_text})
                    sess["queue"].put({"type": "done", "text": ""})
                    sess["done"] = True
                except Exception as _pbe:
                    _chat_log.error(f"[Chat] Playbook command error: {_pbe}")
                    sess["queue"].put({"type": "error", "text": f"Errore comando playbook: {_pbe}"})
                    sess["queue"].put({"type": "done", "text": ""})
                    sess["done"] = True
            
            threading.Thread(target=_handle_pb_command, daemon=True).start()
            return jsonify({"ok": True, "session_id": sid})

        # ── End Playbook slash commands ──────────────────────────────────────

        sm = get_state_manager()
        if sm:
            sm.webui_stop_requested = False  # Clear any stale cancellation flag

        sid  = data.get("session_id") or privacy_manager.get_session_id() or str(uuid.uuid4())
        tab_id = data.get("tab_id")

        # ── Playbook keyword trigger auto-start ──────────────────────────────
        try:
            from hecos.modules.playbooks.playbooks import storage as pb_storage
            from hecos.modules.web_ui.extensions.presenter.feed import add_feed_entry
            sim_state = pb_storage.get_simulation_state(sid)
            active_pbs = [p for p in pb_storage.list_playbooks() if p.get("meta", {}).get("enabled")]
            if active_pbs and sim_state.get("status") == "idle":
                active_pb = active_pbs[0]
                mission = active_pb.get("mission", {})
                kw = (mission.get("start_keyword") or "").strip().lower()
                if kw and kw in user_msg.lower():
                    new_state = pb_storage.start_simulation(sid, active_pb.get("meta", {}).get("id"))
                    raw_u = mission.get("user_role", "User")
                    raw_c = mission.get("chat_role", "Interlocutor")
                    coach_role = mission.get("coach_role", "Coach")
                    is_swapped = new_state.get("swapped", False)
                    u_role = raw_c if is_swapped else raw_u
                    c_role = raw_u if is_swapped else raw_c
                    swap_badge = " (⇄ Ruoli Invertiti)" if is_swapped else ""
                    add_feed_entry("playbook_event", f"▶ Simulation STARTED via keyword '{kw}'{swap_badge} — User: {u_role} · Chat: {c_role} · Coach: {coach_role}", session_id=sid)
        except Exception as _kwe:
            pass
        # ─────────────────────────────────────────────────────────────────────

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
            
            old_overrides = get_session_config(session_id) or {}
            old_p = old_overrides.get("ai", {}).get("active_personality")
            new_p = overrides.get("ai", {}).get("active_personality")
            
            set_session_config(session_id, overrides)
            
            if new_p and new_p != old_p:
                from hecos.core.events import emit
                emit("persona_switched", {"new_persona": new_p.replace(".yaml", "").replace("_", " ")})
                
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
        
        models = get_hybrid_models(cfg_mgr.config, config_manager=cfg_mgr, fast_mode=True)
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
                    yield "data: " + json.dumps({"type": "error", "text": "⛔ Generation aborted."}) + "\n\n"
                    break
                try:
                    ev = sess["queue"].get(timeout=0.5)
                    yield "data: " + json.dumps(ev) + "\n\n"
                    if ev.get("type") in ("error", "done"):
                        break
                except queue.Empty:
                    if sess.get("done") and sess["queue"].empty():
                        yield "data: " + json.dumps({"type": "done", "text": ""}) + "\n\n"
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

