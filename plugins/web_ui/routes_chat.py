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

_sessions      = {}
_sessions_lock = threading.Lock()
_last_audio_path = None
_current_piper_proc = None
_chat_log = logging.getLogger("ZentraChatRoutes")


def _run_inference(session_id: str, user_message: str, history: list, cfg_mgr, images=None):
    sess = _sessions.get(session_id)
    if not sess:
        return

    try:
        from core.llm import brain
    except ImportError as e:
        sess["queue"].put({"type": "error", "text": f"Core non importabile: {e}"})
        sess["done"] = True
        return

    try:
        # Use the shared config manager passed from the plugin server
        risposta = brain.generate_response(user_message, external_config=cfg_mgr.config, images=images)

        # Pass the raw response object to the processor so it can detect and execute tools
        try:
            from core.processing import processore
            full_text, _ = processore.process(risposta, config=cfg_mgr.config)
        except Exception as e:
            _chat_log.error(f"[Chat] Processor error: {e}")
            # Fallback to string if processor fails
            full_text = str(risposta) if isinstance(risposta, str) else "(error during processing)"

        for i in range(0, len(full_text), 40):
            sess["queue"].put({"type": "token", "text": full_text[i:i+40]})
            time.sleep(0.02)

        sess["history"].append({"role": "user",      "content": user_message})
        sess["history"].append({"role": "assistant",  "content": full_text})


        # Save to persistent long-term memory
        try:
            from memory import brain_interface
            brain_interface.save_message("user", user_message, config=cfg_mgr.config)
            brain_interface.save_message("assistant", full_text, config=cfg_mgr.config)
        except Exception as e:
            _chat_log.error(f"[Chat] Memory save error: {e}")


        audio_status = _maybe_generate_tts(full_text, cfg_mgr)
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
        piper_path = voice_cfg.get("piper_path", r"C:\piper\piper.exe")
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

        root = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
        out  = os.path.join(root, "risposta.wav")

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
    Generate a WAV file via Piper for web playback.

    Logic:
      - tts_destination == "system" → play via PC speakers (system audio)
      - tts_destination == "web"    → generate WAV file for browser playback
      - voice_status == False       → skip TTS entirely
    """
    global _last_audio_path
    try:
        from core.audio.device_manager import get_audio_config
        voice_cfg  = get_audio_config()
        
        voice_on   = voice_cfg.get("voice_status", False)
        tts_dest   = voice_cfg.get("tts_destination", "web")
        
        if tts_dest == "system":
            from core.audio import voice
            import threading
            _chat_log.info(f"[Chat] Redirecting TTS to PC speakers: {text[:30]}...")
            threading.Thread(target=voice.speak, args=(text,), daemon=True).start()
            return "system"  # notify UI to show Stop button
            
        if tts_dest != "web":
            return None                     # Not intended for web
            
        if not voice_on:
            return None                     # Voice disabled globally

        path = generate_voice_file(text, voice_cfg)
        if path:
            _last_audio_path = path
            _chat_log.info(f"[Chat] TTS generated successfully -> {path}")
            return "web"
        return None

    except Exception as e:
        _chat_log.debug(f"[Chat] TTS error: {e}")
        return None



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
        images   = data.get("images", [])
        if not user_msg and not images:
            return jsonify({"ok": False, "error": "Empty message"}), 400
        sid  = str(uuid.uuid4())
        sess = {"queue": queue.Queue(), "history": list(history), "done": False}
        with _sessions_lock:
            _sessions[sid] = sess
        threading.Thread(target=_run_inference, args=(sid, user_msg, history, cfg_mgr, images), daemon=True).start()
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
        sid  = request.args.get("session_id", "")
        sess = _sessions.get(sid)
        return jsonify(sess["history"] if sess else [])

    @app.route("/api/audio")
    def api_audio():
        from flask import send_file, jsonify
        if _last_audio_path and os.path.exists(_last_audio_path):
            # Add a timestamp to bust browser cache between responses
            return send_file(_last_audio_path, mimetype="audio/wav",
                             download_name="zentra_response.wav")
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

    @app.route("/static/js/<filename>")
    def serve_static_js(filename):
        from flask import send_from_directory
        js_dir = os.path.join(os.path.dirname(__file__), "static", "js")
        return send_from_directory(js_dir, filename)

    @app.route("/api/images/<filename>")
    def serve_ai_image(filename):
        """
        Serve images from the data/images/ directory.
        The AI can reference images with [[IMG:filename.ext]] syntax.
        Place images in: <zentra-root>/data/images/
        """
        from flask import send_from_directory, jsonify
        images_dir = os.path.join(root_dir, "data", "images")
        os.makedirs(images_dir, exist_ok=True)
        img_path = os.path.join(images_dir, filename)
        if os.path.exists(img_path):
            return send_from_directory(images_dir, filename)
        return jsonify({"error": "Image not found"}), 404
