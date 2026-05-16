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
from flask import jsonify, request, send_from_directory
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
                if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".gif"))
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
