"""
Chat API routes for the native Zentra Web UI.
Provides:
  GET  /                     -> redirect to /chat
  GET  /chat                 -> Chat UI (chat.html)
  POST /api/chat             -> Accept message, start inference, return session_id
  GET  /api/stream/<sid>     -> SSE stream of tokens
  GET  /api/history          -> Session history
  GET  /api/audio            -> Last TTS WAV file
"""
import os
import json
import uuid
import threading
import queue
import time
import logging

_sessions      = {}
_sessions_lock = threading.Lock()
_last_audio_path = None
_chat_log = logging.getLogger("ZentraChatRoutes")


def _run_inference(session_id: str, user_message: str, history: list, cfg_mgr):
    sess = _sessions.get(session_id)
    if not sess:
        return

    try:
        from core.llm import brain
        from app.config import ConfigManager
    except ImportError as e:
        sess["queue"].put({"type": "error", "text": f"Core non importabile: {e}"})
        sess["done"] = True
        return

    try:
        # Use the shared config manager passed from the plugin server
        risposta = brain.generate_response(user_message, external_config=cfg_mgr.config)

        if isinstance(risposta, str):
            full_text = risposta
        else:
            content = getattr(risposta, "content", None)
            if content:
                full_text = str(content)
            else:
                calls = getattr(risposta, "tool_calls", [])
                full_text = " ".join(f"[Tool: {c.function.name}]" for c in calls) or "(risposta non testuale)"

        try:
            from core.processing import processore
            full_text = processore.processa(full_text, cfg.config)
        except Exception:
            pass

        for i in range(0, len(full_text), 40):
            sess["queue"].put({"type": "token", "text": full_text[i:i+40]})
            time.sleep(0.02)

        sess["history"].append({"role": "user",      "content": user_message})
        sess["history"].append({"role": "assistant",  "content": full_text})
        sess["queue"].put({"type": "done", "text": ""})

        _maybe_generate_tts(full_text, cfg_mgr)

    except Exception as exc:
        _chat_log.error(f"[Chat] Inference error: {exc}")
        sess["queue"].put({"type": "error", "text": str(exc)})
    finally:
        sess["done"] = True


def _maybe_generate_tts(text: str, cfg_mgr):
    global _last_audio_path
    try:
        br      = cfg_mgr.config.get("bridge", {})
        voice   = cfg_mgr.config.get("voice", {})

        # We generate TTS for the Web UI if its specific toggle is ON.
        # This works independently of the global 'voice_status' (F5),
        # allowing for 'Silent Console / Audible Web' configurations.
        if not br.get("webui_voice_enabled", False):
            return
        import subprocess
        piper = voce.get("piper_path",   r"C:\piper\piper.exe")
        model = voce.get("onnx_model", "")
        if not os.path.exists(piper) or not model:
            return
        # output at Zentra root
        root = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
        out  = os.path.join(root, "risposta.wav")
        proc = subprocess.Popen(
            [piper, "-m", model, "--output_file", out],
            stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        proc.communicate(input=text.encode("utf-8"))
        if os.path.exists(out):
            _last_audio_path = out
    except Exception as e:
        _chat_log.debug(f"[Chat] TTS error: {e}")


def init_chat_routes(app, cfg_mgr, root_dir: str, logger):

    @app.route("/")
    def root_redirect():
        from flask import redirect
        return redirect("/chat")

    @app.route("/chat")
    def chat_ui():
        from flask import render_template
        try:
            return render_template("chat.html")
        except Exception as e:
            return f"<h1>chat.html non trovato</h1><p>{e}</p>", 500

    @app.route("/api/chat", methods=["POST"])
    def api_chat():
        from flask import request, jsonify
        data     = request.get_json(force=True) or {}
        user_msg = data.get("message", "").strip()
        history  = data.get("history", [])
        if not user_msg:
            return jsonify({"ok": False, "error": "Empty message"}), 400
        sid  = str(uuid.uuid4())
        sess = {"queue": queue.Queue(), "history": list(history), "done": False}
        with _sessions_lock:
            _sessions[sid] = sess
        threading.Thread(target=_run_inference, args=(sid, user_msg, history, cfg_mgr), daemon=True).start()
        return jsonify({"ok": True, "session_id": sid})

    @app.route("/api/stream/<session_id>")
    def api_stream(session_id):
        from flask import Response, stream_with_context
        sess = _sessions.get(session_id)
        if not sess:
            def err():
                yield "data: " + json.dumps({"type": "error", "text": "Session not found"}) + "\n\n"
            return Response(stream_with_context(err()), mimetype="text/event-stream")

        def generate():
            while True:
                try:
                    ev = sess["queue"].get(timeout=30)
                    yield "data: " + json.dumps(ev) + "\n\n"
                    if ev.get("type") in ("done", "error"):
                        break
                except queue.Empty:
                    yield "data: " + json.dumps({"type": "heartbeat"}) + "\n\n"
                    if sess.get("done"):
                        break
            with _sessions_lock:
                _sessions.pop(session_id, None)

        return Response(
            stream_with_context(generate()),
            mimetype="text/event-stream",
            headers={
                "Cache-Control":               "no-cache",
                "X-Accel-Buffering":           "no",
                "Access-Control-Allow-Origin": "*"
            }
        )

    @app.route("/api/history")
    def api_history():
        from flask import request, jsonify
        sid  = request.args.get("session_id", "")
        sess = _sessions.get(sid)
        return jsonify(sess["history"] if sess else [])

    @app.route("/api/audio")
    def api_audio():
        from flask import send_file, jsonify
        if _last_audio_path and os.path.exists(_last_audio_path):
            return send_file(_last_audio_path, mimetype="audio/wav")
        return jsonify({"error": "No audio available"}), 404
