"""
routes_chat_media.py
────────────────────────────────────────────────────────────────────────────
Hecos WebUI — File Upload & Media Serving Routes
Registers:
  POST /api/upload              → process text/image file uploads for context
  GET  /api/images              → list AI-generated images
  GET  /api/images/<filename>   → serve image from media/images/
  POST /api/open_media_folder   → open images folder in OS file explorer
  GET  /media/screenshots/...   → serve screenshots
  GET  /snapshots/...           → legacy screenshot route
  GET  /static/js/<path>        → serve JS static files
  GET  /static/css/<path>       → serve CSS static files
────────────────────────────────────────────────────────────────────────────
"""
import os
import base64
import subprocess
import logging
from flask import jsonify, request, send_from_directory, send_file
from hecos.core.constants import SNAPSHOTS_DIR, IMAGES_DIR

_chat_log = logging.getLogger("HecosChatRoutes")


def init_chat_media_routes(app, logger):

    @app.route("/media/screenshots/<path:filename>")
    def serve_snapshots(filename):
        """Serves captured images from the centralized media/screenshots directory."""
        return send_from_directory(SNAPSHOTS_DIR, filename)

    @app.route("/snapshots/<path:filename>")
    def serve_snapshots_legacy(filename):
        """Legacy route for backward compatibility with old snapshot paths."""
        return send_from_directory(SNAPSHOTS_DIR, filename)

    @app.route("/static/js/<path:filename>")
    def serve_static_js(filename):
        js_dir = os.path.join(os.path.dirname(__file__), "static", "js")
        return send_from_directory(js_dir, filename)

    @app.route("/static/css/<path:filename>")
    def serve_static_css(filename):
        css_dir = os.path.join(os.path.dirname(__file__), "static", "css")
        return send_from_directory(css_dir, filename)

    @app.route("/static/sounds/<path:filename>")
    def serve_static_sounds(filename):
        sounds_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "assets", "sounds"))
        return send_from_directory(sounds_dir, filename)

    @app.route("/api/upload", methods=["POST"])
    def api_upload():
        """
        Accept multipart file uploads.
        - Text files (TXT, MD, CSV, PDF, DOCX): extracted as text context
        - Images (PNG, JPG, JPEG, WEBP): encoded as base64 for vision models
        Returns: {ok, context: str, images: [{name, mime_type, data_b64}], file_count}
        """
        files = request.files.getlist("files")
        if not files:
            return jsonify({"ok": False, "error": "No files received"}), 400

        context_parts = []
        image_parts   = []

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
                        text   = "\n".join(p.extract_text() or "" for p in reader.pages)
                        context_parts.append(f"--- {name} (PDF) ---\n{text}")
                    except ImportError:
                        context_parts.append(f"--- {name} ---\n[pypdf non installato, impossibile leggere il PDF]")

                elif ext == ".docx":
                    try:
                        import docx
                        from io import BytesIO
                        doc  = docx.Document(BytesIO(f.read()))
                        text = "\n".join(p.text for p in doc.paragraphs)
                        context_parts.append(f"--- {name} (DOCX) ---\n{text}")
                    except ImportError:
                        context_parts.append(f"--- {name} ---\n[python-docx non installato, impossibile leggere il DOCX]")

                elif ext in (".png", ".jpg", ".jpeg", ".webp"):
                    raw      = f.read()
                    b64      = base64.b64encode(raw).decode("utf-8")
                    mime_map = {".png": "image/png", ".jpg": "image/jpeg",
                                ".jpeg": "image/jpeg", ".webp": "image/webp"}
                    mime = mime_map.get(ext, "image/jpeg")
                    image_parts.append({"name": name, "mime_type": mime, "data_b64": b64})

                else:
                    context_parts.append(f"--- {name} ---\n[Tipo file non supportato: {ext}]")

            except Exception as e:
                context_parts.append(f"--- {name} ---\n[Errore durante la lettura: {e}]")

        return jsonify({
            "ok":         True,
            "context":    "\n\n".join(context_parts),
            "images":     image_parts,
            "file_count": len(files),
        })

    @app.route("/api/images", methods=["GET"])
    def list_ai_images():
        """Returns a list of all images in the media/images directory (newest first)."""
        os.makedirs(IMAGES_DIR, exist_ok=True)
        try:
            images = [
                {"name": f, "url": f"/api/images/{f}"}
                for f in os.listdir(IMAGES_DIR)
                if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".gif", ".mp4", ".webm", ".avi", ".mov"))
            ]
            images.sort(key=lambda x: os.path.getmtime(os.path.join(IMAGES_DIR, x["name"])), reverse=True)
            return jsonify(images)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/images/<filename>")
    def serve_ai_image(filename):
        """Serves images from the media/images/ directory (referenced by the AI as [[IMG:...]])."""
        os.makedirs(IMAGES_DIR, exist_ok=True)
        img_path = os.path.join(IMAGES_DIR, filename)
        if os.path.exists(img_path):
            return send_from_directory(IMAGES_DIR, filename)
        return jsonify({"error": "Image not found"}), 404

    @app.route("/api/open_media_folder", methods=["POST"])
    def api_open_media_folder():
        """Opens the media/images folder in the OS file manager."""
        os.makedirs(IMAGES_DIR, exist_ok=True)
        try:
            if os.name == "nt":
                os.startfile(IMAGES_DIR)
            else:
                subprocess.Popen(["xdg-open", IMAGES_DIR])
            return jsonify({"ok": True})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500
    @app.route("/api/local_file", methods=["GET"])
    def api_local_file():
        """
        Serves an arbitrary local file from the host machine to the UI.
        Supports HTTP Range requests (required for HTML5 video seeking/streaming).
        """
        import mimetypes
        from flask import Response

        path = request.args.get("path", "")
        if not path or not os.path.exists(path):
            return jsonify({"error": "File not found"}), 404

        try:
            file_size = os.path.getsize(path)
            mime_type, _ = mimetypes.guess_type(path)
            if not mime_type:
                mime_type = "application/octet-stream"

            range_header = request.headers.get("Range")

            if range_header:
                # Parse: "bytes=start-end"
                byte1, byte2 = 0, None
                range_str = range_header.strip().replace("bytes=", "")
                parts = range_str.split("-")
                if parts[0].strip():
                    byte1 = int(parts[0].strip())
                if len(parts) > 1 and parts[1].strip():
                    byte2 = int(parts[1].strip())

                if byte2 is None or byte2 >= file_size:
                    byte2 = file_size - 1

                length = byte2 - byte1 + 1

                with open(path, "rb") as f:
                    f.seek(byte1)
                    data = f.read(length)

                rv = Response(
                    data,
                    status=206,
                    mimetype=mime_type,
                    direct_passthrough=True
                )
                rv.headers["Content-Range"] = f"bytes {byte1}-{byte2}/{file_size}"
                rv.headers["Accept-Ranges"] = "bytes"
                rv.headers["Content-Length"] = str(length)
                rv.headers["Content-Type"] = mime_type
                return rv
            else:
                # No Range header: serve the whole file but advertise range support
                resp = send_file(path, mimetype=mime_type)
                resp.headers["Accept-Ranges"] = "bytes"
                resp.headers["Content-Length"] = str(file_size)
                return resp

        except Exception as e:
            _chat_log.error(f"[ChatMedia] Failed to serve local file {path}: {e}")
            return jsonify({"error": "Failed to serve file"}), 500

    @app.route("/api/open_in_vlc", methods=["POST"])
    def api_open_in_vlc():
        """
        Launches VLC media player on the host machine with the specified local file.
        Since Hecos is a local desktop app, this opens VLC on the user's screen directly.
        """
        data = request.get_json(force=True) or {}
        path = data.get("path", "")
        if not path or not os.path.exists(path):
            return jsonify({"ok": False, "error": "File not found"}), 404

        vlc_candidates = [
            r"C:\Program Files\VideoLAN\VLC\vlc.exe",           # 64-bit standard
            r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",     # 32-bit fallback
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\VideoLAN\VLC\vlc.exe")
        ]

        vlc_exe = None
        for candidate in vlc_candidates:
            if os.path.isfile(candidate):
                vlc_exe = candidate
                break
        
        if not vlc_exe:
            # Fallback to system default if VLC not found
            try:
                os.startfile(path)
                return jsonify({"ok": True, "message": "VLC non trovato. Aperto con il player di sistema."})
            except Exception as e:
                return jsonify({"ok": False, "error": f"VLC not found and fallback failed: {e}"}), 500

        try:
            subprocess.Popen([vlc_exe, path])
            return jsonify({"ok": True})
        except Exception as e:
            _chat_log.error(f"[ChatMedia] Failed to launch VLC: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

