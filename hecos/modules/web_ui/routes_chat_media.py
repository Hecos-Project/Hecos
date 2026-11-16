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
import re
import json
import base64
import subprocess
import logging
from flask import jsonify, request, send_from_directory, send_file
from urllib.parse import quote, unquote
from hecos.core.constants import SNAPSHOTS_DIR, IMAGES_DIR, MEDIA_DIR

_chat_log = logging.getLogger("HecosChatRoutes")

_MEDIA_SKIP_SCHEMES = (
    "http://", "https://", "//", "data:", "blob:", "mailto:", "tel:", "javascript:", "#", "/api/"
)


def _resolve_local_media_candidate(raw: str, base_dir: str = "", *, allow_base_relative: bool = True) -> str | None:
    """Resolve an explicit file:// / drive path or local media reference to an existing file on disk."""
    val = unquote((raw or "").strip())
    if not val:
        return None
    clean_no_q = val.split("#", 1)[0].split("?", 1)[0].strip()
    if not clean_no_q:
        return None

    # 1. Explicit file:// URI or Windows drive path (e.g. C:/Hecos/hecos/media/Images/Urania.png)
    if clean_no_q.lower().startswith("file:///"):
        p = clean_no_q[8:].replace("/", os.sep)
        if os.path.isfile(p):
            return os.path.abspath(p)
    elif clean_no_q.lower().startswith("file://"):
        p = clean_no_q[7:].replace("/", os.sep)
        if os.path.isfile(p):
            return os.path.abspath(p)
    elif len(clean_no_q) > 2 and clean_no_q[1] == ":" and clean_no_q[0].isalpha():
        p = clean_no_q.replace("/", os.sep)
        if os.path.isfile(p):
            return os.path.abspath(p)

    # 2. Project-relative path inside base_dir (used by /api/serve_html)
    rel_clean = clean_no_q.lstrip("/\\").replace("/", os.sep)
    if allow_base_relative and base_dir and os.path.isdir(base_dir):
        candidate = os.path.normpath(os.path.join(base_dir, rel_clean))
        try:
            if os.path.commonpath([os.path.abspath(base_dir), candidate]) == os.path.abspath(base_dir) and os.path.isfile(candidate):
                return os.path.abspath(candidate)
        except ValueError:
            pass

    # 3. Fallback to Hecos MEDIA_DIR / IMAGES_DIR when a path points to images/media outside project root
    low_slashes = clean_no_q.replace("\\", "/").lower()
    if not (allow_base_relative and base_dir and os.path.isfile(os.path.join(base_dir, rel_clean))):
        # Skip plain local asset names when running behind app proxy unless present in IMAGES_DIR
        bname = os.path.basename(rel_clean)
        for root_cand in (MEDIA_DIR, IMAGES_DIR):
            if not root_cand or not os.path.isdir(root_cand):
                continue
            cand_direct = os.path.normpath(os.path.join(root_cand, rel_clean))
            try:
                if os.path.commonpath([os.path.abspath(root_cand), cand_direct]) == os.path.abspath(root_cand) and os.path.isfile(cand_direct):
                    return os.path.abspath(cand_direct)
            except ValueError:
                pass
            if bname and ("images/" in low_slashes or not allow_base_relative):
                cand_base = os.path.join(root_cand, bname)
                if os.path.isfile(cand_base):
                    return os.path.abspath(cand_base)
    return None


def rewrite_html_local_media_refs(
    html: str,
    base_dir: str = "",
    *,
    rewrite_relative: bool = True,
) -> str:
    """
    Rewrite file://, Windows drive paths (C:/...), and optional project-relative local
    media references in src/href/poster/data-src and CSS url(...) to /api/local_file?path=...
    """
    if not html:
        return html

    def _rewrite_attr(m):
        prefix, value, suffix = m.group(1), m.group(2), m.group(3)
        val_low = value.strip().lower()
        if not val_low:
            return m.group(0)
        is_abs_or_file = (
            val_low.startswith("file://")
            or (len(value.strip()) > 2 and value.strip()[1] == ":" and value.strip()[0].isalpha())
        )
        if not is_abs_or_file and val_low.startswith(_MEDIA_SKIP_SCHEMES):
            return m.group(0)

        resolved = _resolve_local_media_candidate(
            value,
            base_dir=base_dir,
            allow_base_relative=rewrite_relative,
        )
        if resolved:
            return prefix + f"/api/local_file?path={quote(resolved)}" + suffix
        return m.group(0)

    out = re.sub(
        r'((?:src|href|poster|data-src)=["\'])([^"\']+)(["\'])',
        _rewrite_attr,
        html,
        flags=re.IGNORECASE,
    )
    out = re.sub(
        r'(url\(["\']?)([^"\')\s]+)(["\']?\))',
        _rewrite_attr,
        out,
        flags=re.IGNORECASE,
    )
    return out


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
        saved_files   = []

        docs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "media", "documents")
        os.makedirs(docs_dir, exist_ok=True)
        os.makedirs(IMAGES_DIR, exist_ok=True)

        for f in files:
            name = f.filename or "unknown"
            ext  = os.path.splitext(name)[1].lower()
            raw_data = f.read()

            try:
                if ext in (".txt", ".md", ".csv", ".html"):
                    text = raw_data.decode("utf-8", errors="replace")
                    context_parts.append(f"--- {name} ---\n{text}")
                    # Save to disk
                    save_path = os.path.join(docs_dir, name)
                    with open(save_path, "wb") as out:
                        out.write(raw_data)
                    norm_path = save_path.replace("\\", "/")
                    saved_files.append({"name": name, "path": norm_path, "url": f"/api/local_file?path={quote(norm_path)}"})

                elif ext == ".pdf":
                    try:
                        import pypdf
                        from io import BytesIO
                        reader = pypdf.PdfReader(BytesIO(raw_data))
                        text   = "\n".join(p.extract_text() or "" for p in reader.pages)
                        context_parts.append(f"--- {name} (PDF) ---\n{text}")
                    except ImportError:
                        context_parts.append(f"--- {name} ---\n[pypdf non installato, impossibile leggere il PDF]")
                    # Save to disk
                    save_path = os.path.join(docs_dir, name)
                    with open(save_path, "wb") as out:
                        out.write(raw_data)
                    norm_path = save_path.replace("\\", "/")
                    saved_files.append({"name": name, "path": norm_path, "url": f"/api/local_file?path={quote(norm_path)}"})

                elif ext == ".docx":
                    try:
                        import docx
                        from io import BytesIO
                        doc  = docx.Document(BytesIO(raw_data))
                        text = "\n".join(p.text for p in doc.paragraphs)
                        context_parts.append(f"--- {name} (DOCX) ---\n{text}")
                    except ImportError:
                        context_parts.append(f"--- {name} ---\n[python-docx non installato, impossibile leggere il DOCX]")
                    # Save to disk
                    save_path = os.path.join(docs_dir, name)
                    with open(save_path, "wb") as out:
                        out.write(raw_data)
                    norm_path = save_path.replace("\\", "/")
                    saved_files.append({"name": name, "path": norm_path, "url": f"/api/local_file?path={quote(norm_path)}"})

                elif ext in (".png", ".jpg", ".jpeg", ".webp"):
                    b64      = base64.b64encode(raw_data).decode("utf-8")
                    mime_map = {".png": "image/png", ".jpg": "image/jpeg",
                                ".jpeg": "image/jpeg", ".webp": "image/webp"}
                    mime = mime_map.get(ext, "image/jpeg")
                    image_parts.append({"name": name, "mime_type": mime, "data_b64": b64})
                    # Save to disk
                    save_path = os.path.join(IMAGES_DIR, name)
                    with open(save_path, "wb") as out:
                        out.write(raw_data)
                    norm_path = save_path.replace("\\", "/")
                    saved_files.append({"name": name, "path": norm_path, "url": f"/api/images/{name}"})

                else:
                    context_parts.append(f"--- {name} ---\n[Tipo file non supportato: {ext}]")
                    # Save unknown files anyway
                    save_path = os.path.join(docs_dir, name)
                    with open(save_path, "wb") as out:
                        out.write(raw_data)
                    norm_path = save_path.replace("\\", "/")
                    saved_files.append({"name": name, "path": norm_path, "url": f"/api/local_file?path={quote(norm_path)}"})

            except Exception as e:
                context_parts.append(f"--- {name} ---\n[Errore durante la lettura: {e}]")

        return jsonify({
            "ok":         True,
            "context":    "\n\n".join(context_parts),
            "images":     image_parts,
            "saved_files": saved_files,
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

    @app.route("/api/open_media_folder", methods=["GET", "POST"])
    def api_open_media_folder():
        """Opens the centralized media folder (or subfolder) in the native OS file manager."""
        target = request.args.get("target") or (request.get_json(silent=True) or {}).get("target")
        folder = IMAGES_DIR if target == "images" else MEDIA_DIR
        os.makedirs(folder, exist_ok=True)
        try:
            from hecos.core.system.os_adapter import OSAdapter
            details = OSAdapter.open_path_detailed(folder)
            if details.get("ok"):
                return jsonify({"ok": True, "path": folder, "details": details})
            return jsonify({"ok": False, "error": details.get("error") or "Native file manager failed to launch", "details": details}), 500
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500
    @app.route("/api/serve_html", methods=["GET"])
    def api_serve_html():
        """
        Serves a local HTML file with all internal file:// and absolute-path references
        rewritten to use /api/local_file, so the browser can load images/assets without
        hitting same-origin or mixed-content restrictions.
        """
        import re
        from flask import Response

        path = request.args.get("path", "")
        while "?path=" in path:
            path = unquote(path.split("?path=", 1)[1])
        if not path or not os.path.exists(path):
            return jsonify({"error": "File not found"}), 404

        ext = os.path.splitext(path)[1].lower()
        if ext not in (".html", ".htm"):
            return jsonify({"error": "Not an HTML file"}), 400

        try:
            abs_html_path = os.path.abspath(path)
            if request.args.get("static") not in ("1", "true"):
                try:
                    from hecos.modules.web_ui.routes_workspace_runner import (
                        find_matching_running_app,
                        proxy_workspace_run_request,
                    )

                    matched = find_matching_running_app(abs_html_path)
                    if matched and matched.get("run_id"):
                        return proxy_workspace_run_request(matched["run_id"], "")
                except Exception:
                    pass

            base_dir = os.path.dirname(abs_html_path)
            with open(abs_html_path, "r", encoding="utf-8", errors="replace") as f:
                html = f.read()

            html = rewrite_html_local_media_refs(html, base_dir=base_dir, rewrite_relative=True)
            return Response(html, status=200, mimetype="text/html; charset=utf-8")

        except Exception as e:
            _chat_log.error(f"[ChatMedia] Failed to serve HTML {path}: {e}")
            return jsonify({"error": "Failed to serve HTML"}), 500

    @app.route("/api/local_file", methods=["GET"])
    def api_local_file():
        """
        Serves an arbitrary local file from the host machine to the UI.
        Supports HTTP Range requests (required for HTML5 video seeking/streaming).
        """
        import mimetypes
        from flask import Response

        path = request.args.get("path", "")
        # Recursively unwrap if path was nested inside /api/local_file?path= or URL-encoded
        while "?path=" in path:
            path = unquote(path.split("?path=", 1)[1])
        path = path.replace("\\", "/")

        # If path does not exist directly, try resolving candidate files
        if not path or not os.path.exists(path):
            docs_dir = os.path.join(MEDIA_DIR, "documents")
            workspace_dir = os.path.join(MEDIA_DIR, "workspace")
            basename = os.path.basename(path)
            candidate_doc = os.path.join(docs_dir, basename)
            candidate_ws = os.path.join(workspace_dir, basename)
            if os.path.exists(candidate_doc):
                path = candidate_doc
            elif os.path.exists(candidate_ws):
                path = candidate_ws
            else:
                # Match if filename was concatenated without slashes (e.g. C:Hecos...file.pdf)
                matched = False
                if os.path.exists(docs_dir):
                    for fname in os.listdir(docs_dir):
                        if path.lower().endswith(fname.lower()):
                            candidate_match = os.path.join(docs_dir, fname)
                            if os.path.exists(candidate_match):
                                path = candidate_match
                                matched = True
                                break
                if not matched and os.path.exists(IMAGES_DIR):
                    for fname in os.listdir(IMAGES_DIR):
                        if path.lower().endswith(fname.lower()):
                            candidate_match = os.path.join(IMAGES_DIR, fname)
                            if os.path.exists(candidate_match):
                                path = candidate_match
                                matched = True
                                break
                if not matched and not os.path.exists(path):
                    return jsonify({"error": "File not found"}), 404

        try:
            file_size = os.path.getsize(path)
            ext_low = os.path.splitext(path)[1].lower()
            _explicit_mimes = {
                ".css": "text/css; charset=utf-8",
                ".js": "application/javascript; charset=utf-8",
                ".mjs": "application/javascript; charset=utf-8",
                ".html": "text/html; charset=utf-8",
                ".htm": "text/html; charset=utf-8",
                ".svg": "image/svg+xml",
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".webp": "image/webp",
                ".gif": "image/gif",
                ".mp4": "video/mp4",
                ".webm": "video/webm",
                ".mp3": "audio/mpeg",
                ".wav": "audio/wav",
            }
            mime_type = _explicit_mimes.get(ext_low)
            if not mime_type:
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
                rv.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
                rv.headers["Pragma"] = "no-cache"
                rv.headers["Expires"] = "0"
                return rv
            else:
                # No Range header: serve the whole file but advertise range support
                resp = send_file(path, mimetype=mime_type)
                resp.headers["Accept-Ranges"] = "bytes"
                resp.headers["Content-Length"] = str(file_size)
                resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
                resp.headers["Pragma"] = "no-cache"
                resp.headers["Expires"] = "0"
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

    # ── Fallback Document Maker routes ─────────────────────────────────────────
    # These mirror the plugin routes so the Visual Editor works even when
    # the HPM plugin route registration hasn't fired (e.g. after a rebuild).

    @app.route("/hecos/api/plugins/document_maker/preview", methods=["GET"])
    def doc_preview_get_fallback():
        """Read a document file and return its HTML content for the Visual Editor."""
        path = request.args.get("path")
        if not path or not os.path.exists(path):
            return jsonify({"ok": False, "error": "File not found"}), 404
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            return jsonify({"ok": True, "html": content})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/hecos/api/plugins/document_maker/preview", methods=["POST"])
    def doc_preview_post_fallback():
        """Save edited HTML and regenerate PDF from the Visual Editor."""
        try:
            data = request.get_json(force=True)
            path = data.get("path")
            html = data.get("html")
            if not path or not html:
                return jsonify({"ok": False, "error": "Missing path or html"}), 400
            with open(path, "w", encoding="utf-8") as f:
                f.write(html)
            if path.endswith(".html"):
                pdf_path = path[:-5] + ".pdf"
                try:
                    from hecos.hpm.document_maker.main import DocsTools
                    dt = DocsTools()
                    processed = dt._resolve_image_paths(html)
                    processed = dt._inject_pagination_css(processed)
                    res = dt._generate_pdf_from_html(processed, pdf_path)
                    if not res:
                        return jsonify({"ok": False, "error": "PDF regeneration failed"}), 500
                except Exception as e:
                    return jsonify({"ok": False, "error": str(e)}), 500
            return jsonify({"ok": True})
        except Exception as e:
            _chat_log.error(f"[ChatMedia] doc_preview POST error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/hecos/api/plugins/document_maker/generate_pdf_from_html", methods=["POST"])
    def doc_generate_pdf_from_editor_fallback():
        """Save edited HTML from editor and regenerate PDF."""
        try:
            data = request.get_json(force=True)
            filepath = data.get("filepath")
            html = data.get("html")
            if not filepath or not html:
                return jsonify({"ok": False, "error": "Missing filepath or html"}), 400
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(html)
            pdf_path = filepath.rsplit(".", 1)[0] + ".pdf"
            try:
                from hecos.hpm.document_maker.main import DocsTools
                dt = DocsTools()
                resolved = dt._resolve_image_paths(html)
                resolved = dt._inject_pagination_css(resolved)
                result = dt._generate_pdf_from_html(resolved, pdf_path)
                if result and os.path.exists(result):
                    pdf_url = f"/api/local_file?path={os.path.normpath(result).replace(os.sep, '/')}"
                    return jsonify({"ok": True, "pdf_url": pdf_url})
                return jsonify({"ok": False, "error": "PDF generation failed"}), 500
            except Exception as e:
                return jsonify({"ok": False, "error": str(e)}), 500
        except Exception as e:
            _chat_log.error(f"[ChatMedia] doc_generate_pdf_from_editor error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/hecos/api/plugins/document_maker/config", methods=["GET"])
    def doc_config_get():
        """Get Document Maker configuration."""
        try:
            hecos_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            cfg_path = os.path.join(hecos_root, "hecos", "hpm", "document_maker", "docs_config.json")
            if not os.path.exists(cfg_path):
                cfg_path = os.path.join(hecos_root, "hpm", "document_maker", "docs_config.json")
            data = {}
            if os.path.exists(cfg_path):
                with open(cfg_path, "r", encoding="utf-8-sig") as f:
                    data = json.load(f)
            return jsonify(data)
        except Exception as e:
            _chat_log.error(f"[ChatMedia] doc_config GET error: {e}")
            return jsonify({}), 500

    @app.route("/hecos/api/plugins/document_maker/config", methods=["POST"])
    def doc_config_post():
        """Save Document Maker configuration."""
        try:
            payload = request.get_json(force=True) or {}
            hecos_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            paths = [
                os.path.join(hecos_root, "hecos", "hpm", "document_maker", "docs_config.json"),
                os.path.join(hecos_root, "hpm", "document_maker", "docs_config.json"),
                os.path.join("C:\\Hecos-Packages\\sources\\plugins\\document_maker_src", "docs_config.json")
            ]
            saved = False
            for p in paths:
                try:
                    os.makedirs(os.path.dirname(p), exist_ok=True)
                    with open(p, "w", encoding="utf-8") as f:
                        json.dump(payload, f, indent=4, ensure_ascii=False)
                    saved = True
                except Exception:
                    pass
            if saved:
                return jsonify({"ok": True})
            return jsonify({"ok": False, "error": "Could not write config"}), 500
        except Exception as e:
            _chat_log.error(f"[ChatMedia] doc_config POST error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/hecos/api/plugins/document_maker/templates", methods=["GET"])
    def doc_templates_get():
        """Return available templates for Document Maker."""
        try:
            hecos_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            tpl_file = os.path.join(hecos_root, "hecos", "data", "templates.json")
            if not os.path.exists(tpl_file):
                tpl_file = os.path.join(hecos_root, "data", "templates.json")
            templates = []
            if os.path.exists(tpl_file):
                with open(tpl_file, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                items = raw.values() if isinstance(raw, dict) else raw
                for t in items:
                    if t.get("channel") in ("document", "doc") or "doc" in t.get("id", "") or "rivista" in t.get("name", "").lower():
                        templates.append({
                            "id": t.get("id"),
                            "name": t.get("name"),
                            "channel": t.get("channel", "document"),
                            "description": t.get("description", ""),
                            "variables": t.get("variables", []),
                            "body_html": t.get("body_html", ""),
                            "body_text": t.get("body_text", "")
                        })
            return jsonify({"ok": True, "templates": templates, "count": len(templates)})
        except Exception as e:
            _chat_log.error(f"[ChatMedia] doc_templates GET error: {e}")
            return jsonify({"ok": False, "templates": [], "error": str(e)}), 500


