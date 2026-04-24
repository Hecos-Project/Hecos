"""
Chat API routes for the native Zentra Web UI.
Provides:
  GET  /                     -> redirect to /chat
  GET  /chat                 -> Chat UI (chat.html)
  POST /api/chat             -> Accept message, start inference, return session_id
  GET  /api/stream/<sid>     -> SSE stream of tokens
  GET  /api/history          -> Session history
  GET  /api/audio            -> Last TTS WAV file (for web playback)
"""
import os
import json
import uuid
import threading
import queue
import time
import logging
from zentra.core.constants import LOGS_DIR, SNAPSHOTS_DIR, IMAGES_DIR, AUDIO_DIR

_sessions      = {}
_sessions_lock = threading.Lock()
_last_audio_path = None
_current_piper_proc = None
_chat_log = logging.getLogger("ZentraChatRoutes")

def set_last_audio_path(path: str):
    global _last_audio_path
    _last_audio_path = path
    _chat_log.info(f"[Audio] Global _last_audio_path updated to: {path}")


def _run_inference(session_id: str, user_message: str, history: list, cfg_mgr, images=None, user_id="admin"):
    sess = _sessions.get(session_id)
    if not sess:
        return

    try:
        from zentra.core.llm import brain
    except ImportError as e:
        sess["queue"].put({"type": "error", "text": f"Core non importabile: {e}"})
        sess["done"] = True
        return

    try:
        from zentra.core.agent.loop import AgentExecutor
        from modules.web_ui.server import get_state_manager
        
        # Instantiate AgentExecutor with shared config and live StateManager
        sm = get_state_manager()
        
        # ── Session-Aware Trace Callback ─────────────────────────────────────
        # Instead of relying on the global /api/events bus (which the browser
        # may not be polling during inference), we inject traces DIRECTLY into
        # the session-specific SSE queue that the browser is already reading.
        def _session_trace(msg: str, level: str = "info"):
            sess["queue"].put({
                "type":    "agent_trace",
                "level":   level,
                "message": msg
            })
        # ─────────────────────────────────────────────────────────────────────

        agent = AgentExecutor(config=cfg_mgr.config, config_manager=cfg_mgr, state_manager=sm, trace_callback=_session_trace, current_user_id=user_id)
        
        # ── SSE Connection Buffer ─────────────────────────────────────────────
        # The browser receives session_id from POST /api/chat, then must open a
        # SECOND request to GET /api/stream/<sid>. Without this pause, the first
        # agent_trace events are put into the queue BEFORE the browser connects
        # to the SSE stream, causing them to be lost silently.
        time.sleep(0.4)
        # ─────────────────────────────────────────────────────────────────────
        
        # Ensure voice string is processed by the processore.py properly isolating text/voice filters
        full_text, clean_voice = agent.run_agentic_loop(user_message, voice_status=True, images=images)

        # ── Client Camera Interceptor ────────────────────────────────────────────
        # Check for [CAMERA_SNAPSHOT_REQUEST] BEFORE the 40-char chunking loop.
        # If intercepted in the loop, the token gets split across chunks and the
        # browser JS never sees it as a complete string — this is far more reliable.
        _CAMERA_TOKEN = "[CAMERA_SNAPSHOT_REQUEST]"
        camera_request_pending = _CAMERA_TOKEN in (full_text or "")
        if camera_request_pending:
            full_text = full_text.replace(_CAMERA_TOKEN, "").strip()
        # ────────────────────────────────────────────────────────────────────────

        for i in range(0, len(full_text), 40):
            sess["queue"].put({"type": "token", "text": full_text[i:i+40]})
            time.sleep(0.02)

        # ── Finalize agent trace bubble BEFORE (blocking) TTS synthesis ──────────
        # This lets the frontend stop the ⚙️ spinner as soon as the text response
        # is fully rendered, without waiting for Piper to finish generating audio.
        sess["queue"].put({"type": "trace_done"})
        # ─────────────────────────────────────────────────────────────────────────

        # Emit camera request event AFTER the text tokens so it appears last
        if camera_request_pending:
            sess["queue"].put({"type": "camera_request"})

        sess["history"].append({"role": "user",      "content": user_message})
        sess["history"].append({"role": "assistant",  "content": full_text})

        # Send the isolated voice string to the TTS engine, NOT the text string
        audio_status = _maybe_generate_tts(clean_voice, cfg_mgr)
        if audio_status == "web":
            sess["queue"].put({"type": "audio_ready", "text": ""})
        elif audio_status == "system":
            sess["queue"].put({"type": "system_audio_playing", "text": ""})
            
        # Signal completion to UI only after audio events are queued
        sess["queue"].put({"type": "done", "text": ""})

    except Exception as exc:
        _chat_log.error(f"[Chat] Inference error: {exc}")
        sess["queue"].put({"type": "error", "text": str(exc)})
    finally:
        sess["done"] = True


def generate_voice_file(text: str, voice_cfg: dict) -> str:
    """
    Core function to run Piper and create risposta.wav.
    Returns the absolute path to the generated WAV, or None on failure.
    """
    try:
        # Dynamically resolve Zentra root directory (from web_ui/routes_chat.py going up to root)
        zentra_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        default_piper_dir = os.path.join(zentra_root, 'bin', 'piper')
        is_windows = os.name == 'nt'
        piper_exe_name = 'piper.exe' if is_windows else 'piper'
        
        piper_path = voice_cfg.get("piper_path", os.path.join(default_piper_dir, piper_exe_name))
        model_path = voice_cfg.get("onnx_model", "")
        
        if not os.path.exists(piper_path):
            _chat_log.info(f"[Audio] Piper.exe not found at {piper_path}")
            return None
        if not os.path.exists(model_path):
            _chat_log.info(f"[Audio] ONNX model not found at {model_path}")
            return None

        # Build flags
        length_scale     = 1.0 / max(0.1, voice_cfg.get("speed", 1.0))
        noise_scale      = voice_cfg.get("noise_scale", 0.667)
        noise_w          = voice_cfg.get("noise_w", 0.8)
        sentence_silence = voice_cfg.get("sentence_silence", 0.2)

        # risposta.wav in zentra/media/audio/
        out = os.path.join(AUDIO_DIR, "risposta.wav")

        import subprocess
        clean_text = text.replace('"', '').replace('\n', ' ')
        command = [
            piper_path, "-m", model_path,
            "--length_scale",     str(length_scale),
            "--noise_scale",      str(noise_scale),
            "--noise_w",          str(noise_w),
            "--sentence_silence", str(sentence_silence),
            "-f", out,
        ]
        
        _chat_log.info(f"[Audio] Piper command: {' '.join(command)}")
        global _current_piper_proc
        proc = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        _current_piper_proc = proc
        stdout, stderr = proc.communicate(input=clean_text.encode("utf-8"))
        _current_piper_proc = None

        if proc.returncode != 0:
            _chat_log.error(f"[Audio] Piper failed (code {proc.returncode}): {stderr.decode('utf-8', errors='ignore')}")
            return None

        if os.path.exists(out):
            return out
        return None
    except Exception as e:
        _chat_log.error(f"[Audio] generate_voice_file error: {e}")
        return None


def stop_voice_generation():
    """Immediately kills any active Piper generation for the browser output."""
    global _current_piper_proc
    if _current_piper_proc is not None:
        try:
            pid = _current_piper_proc.pid
            _chat_log.info(f"[Audio] Killing active web Piper process {pid}...")
            _current_piper_proc.terminate()
        except Exception as e:
            _chat_log.error(f"[Audio] Failed to terminate web Piper: {e}")
        finally:
            _current_piper_proc = None

def _maybe_generate_tts(text: str, cfg_mgr):
    """
    Generate TTS audio for the WebUI.
    Since this route is used exclusively by the WebUI client, we unconditionally 
    generate a WAV file and defer playback to the browser's audio context.
    """
    global _last_audio_path
    try:
        from zentra.core.audio.device_manager import get_audio_config
        voice_cfg  = get_audio_config()
        voice_on   = voice_cfg.get("voice_status", False)

        if not voice_on:
            _chat_log.debug("[Chat] TTS skipped: voice_status=False.")
            return None

        path = generate_voice_file(text, voice_cfg)
        if path:
            _last_audio_path = path
            _chat_log.info(f"[Chat] TTS → browser WAV: {path}")
            return "web"
            
        return None
    except Exception as e:
        _chat_log.debug(f"[Chat] TTS error: {e}")
        return None




def init_chat_routes(app, cfg_mgr, root_dir: str, logger):
    from flask import send_from_directory
    
    @app.route("/media/screenshots/<path:filename>")
    def serve_snapshots(filename):
        """Serves captured images from the centralized media/screenshots directory."""
        return send_from_directory(SNAPSHOTS_DIR, filename)

    @app.route("/snapshots/<path:filename>")
    def serve_snapshots_legacy(filename):
        """Legacy route kept for backward compatibility with old snapshot paths."""
        return send_from_directory(SNAPSHOTS_DIR, filename)

    @app.route("/")
    def root_redirect():
        from flask import redirect
        return redirect("/chat")

    @app.route("/chat")
    def chat_ui():
        from flask import render_template, make_response
        from flask_login import current_user
        from zentra.core.auth.auth_manager import auth_mgr
        from zentra.core.i18n.translator import get_translator
        try:
            profile = auth_mgr.get_profile(current_user.username) if current_user.is_authenticated else None
            translations = get_translator().get_translations()
            # Pass Zentra config as 'zconfig' to avoid conflict with Flask's 'config'
            resp = make_response(render_template("chat.html", profile=profile, zconfig=cfg_mgr.config, translations=translations))
            resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            resp.headers["Pragma"] = "no-cache"
            return resp
        except Exception as e:
            return f"<h1>chat.html non trovato</h1><p>{e}</p>", 500

    @app.route("/api/chat", methods=["POST"])
    def api_chat():
        from flask import request, jsonify
        from flask_login import current_user
        data     = request.get_json(force=True) or {}
        user_msg = data.get("message", "").strip()
        history  = data.get("history", [])
        images   = data.get("images", [])
        if not user_msg and not images:
            return jsonify({"ok": False, "error": "Empty message"}), 400
            
        uid = current_user.username if current_user.is_authenticated else "admin"
        
        from zentra.core.privacy import privacy_manager
        sid = data.get("session_id") or privacy_manager.get_session_id() or str(uuid.uuid4())
        
        sess = {"queue": queue.Queue(), "history": list(history), "done": False, "user_id": uid}
        with _sessions_lock:
            _sessions[sid] = sess
        threading.Thread(target=_run_inference, args=(sid, user_msg, history, cfg_mgr, images, uid), daemon=True).start()
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
                    # Shorter timeout to check sess["done"] frequently 
                    ev = sess["queue"].get(timeout=0.5)
                    if ev.get("type") == "agent_trace":
                        pass
                    yield "data: " + json.dumps(ev) + "\n\n"
                    if ev.get("type") == "error":
                        break
                except queue.Empty:
                    # If inference is officially finished AND no more events are queued, we can exit
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
                "Access-Control-Allow-Origin": "*"
            }
        )

    @app.route("/api/history")
    def api_history():
        from flask import request, jsonify
        from flask_login import current_user
        from zentra.memory.brain_interface import get_history
        from zentra.core.privacy import privacy_manager
        
        uid = current_user.username if current_user.is_authenticated else "admin"
        sid = privacy_manager.get_session_id()
        
        hist = get_history(user_id=uid, session_id=sid)
        return jsonify([{"role": role, "content": msg} for role, msg in hist])

    @app.route("/api/audio")
    def api_audio():
        from flask import send_file, jsonify
        _chat_log.debug(f"[Audio] GET /api/audio requested. Last path: {_last_audio_path}")
        if _last_audio_path and os.path.exists(_last_audio_path):
            return send_file(_last_audio_path, mimetype="audio/wav",
                             download_name="zentra_response.wav")
        _chat_log.warning(f"[Audio] GET /api/audio failed. Path not found or empty: {_last_audio_path}")
        return jsonify({"error": "No audio available"}), 404

    @app.route("/api/upload", methods=["POST"])
    def api_upload():
        """Accept multipart file uploads.
        - Text files (TXT, MD, CSV, PDF, DOCX): extracted as text context
        - Images (PNG, JPG, JPEG, WEBP): encoded as base64 for vision models
        Returns: {ok, context: str, images: [{name, mime_type, data_b64}], file_count}
        """
        from flask import request, jsonify
        import base64
        files = request.files.getlist("files")
        if not files:
            return jsonify({"ok": False, "error": "No files received"}), 400

        context_parts = []
        image_parts = []  # List of {name, mime_type, data_b64}

        for f in files:
            name = f.filename or "unknown"
            ext  = os.path.splitext(name)[1].lower()
            try:
                if ext in (".txt", ".md", ".csv"):
                    text = f.read().decode("utf-8", errors="replace")
                    context_parts.append(f"--- {name} ---\n{text}")

                elif ext == ".pdf":
                    try:
                        import pypdf
                        from io import BytesIO
                        reader = pypdf.PdfReader(BytesIO(f.read()))
                        text = "\n".join(p.extract_text() or "" for p in reader.pages)
                        context_parts.append(f"--- {name} (PDF) ---\n{text}")
                    except ImportError:
                        context_parts.append(f"--- {name} ---\n[pypdf non installato, impossibile leggere il PDF]")

                elif ext == ".docx":
                    try:
                        import docx
                        from io import BytesIO
                        doc = docx.Document(BytesIO(f.read()))
                        text = "\n".join(p.text for p in doc.paragraphs)
                        context_parts.append(f"--- {name} (DOCX) ---\n{text}")
                    except ImportError:
                        context_parts.append(f"--- {name} ---\n[python-docx non installato, impossibile leggere il DOCX]")

                elif ext in (".png", ".jpg", ".jpeg", ".webp"):
                    # Encode image as base64 for vision models
                    raw = f.read()
                    b64 = base64.b64encode(raw).decode("utf-8")
                    mime_map = {".png": "image/png", ".jpg": "image/jpeg",
                                ".jpeg": "image/jpeg", ".webp": "image/webp"}
                    mime = mime_map.get(ext, "image/jpeg")
                    image_parts.append({"name": name, "mime_type": mime, "data_b64": b64})

                else:
                    context_parts.append(f"--- {name} ---\n[Tipo file non supportato: {ext}]")

            except Exception as e:
                context_parts.append(f"--- {name} ---\n[Errore durante la lettura: {e}]")

        combined = "\n\n".join(context_parts)
        return jsonify({
            "ok": True,
            "context": combined,
            "images": image_parts,
            "file_count": len(files)
        })

    @app.route("/static/js/<path:filename>")
    def serve_static_js(filename):
        from flask import send_from_directory
        js_dir = os.path.join(os.path.dirname(__file__), "static", "js")
        return send_from_directory(js_dir, filename)

    @app.route("/static/css/<path:filename>")
    def serve_static_css(filename):
        from flask import send_from_directory
        css_dir = os.path.join(os.path.dirname(__file__), "static", "css")
        return send_from_directory(css_dir, filename)

    @app.route("/api/images/<filename>")
    def serve_ai_image(filename):
        """
        Serve images from the centralized media/images/ directory.
        The AI can reference images with [[IMG:filename.ext]] syntax.
        """
        from flask import send_from_directory, jsonify
        os.makedirs(IMAGES_DIR, exist_ok=True)
        img_path = os.path.join(IMAGES_DIR, filename)
        if os.path.exists(img_path):
            return send_from_directory(IMAGES_DIR, filename)
        return jsonify({"error": "Image not found"}), 404
