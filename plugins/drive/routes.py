"""
Plugin: Zentra Drive — Routes
REST API for the HTTP File Manager.
All routes require authentication.
"""

import os
import shutil
from flask import request, jsonify, send_file, render_template, abort
from flask_login import login_required, current_user
from core.logging import logger


def _safe_path(root: str, rel_path: str) -> str | None:
    """
    Resolves a relative path against the drive root.
    Returns None if path traversal is detected (outside root).
    """
    # Normalize and resolve the candidate path
    candidate = os.path.normpath(os.path.join(root, rel_path.lstrip("/\\")))
    candidate = os.path.abspath(candidate)
    root_abs = os.path.abspath(root)
    
    # Security: path must start with root
    if not candidate.startswith(root_abs):
        return None
    return candidate


def init_drive_routes(app, logger_instance=None):
    """Registers all /drive/* routes on the Flask app."""
    _log = logger_instance or logger

    from .main import get_plugin
    plugin = get_plugin()

    # ─── Load Extensions ────────────────────────────────────────────────────────
    # Register the Code Editor extension routes immediately (it adds /drive/editor)
    try:
        from core.system.extension_loader import load_extension_routes, discover_extensions
        plugin_dir = os.path.dirname(os.path.abspath(__file__))
        discover_extensions("DRIVE", plugin_dir)
        load_extension_routes(app, "DRIVE", "editor")
    except Exception as _ext_err:
        _log.error(f"[Drive] Failed to load editor extension: {_ext_err}")
    # ────────────────────────────────────────────────────────────────────────────

    # ─── PAGE ──────────────────────────────────────────────────────────────────

    @app.route("/drive")
    @app.route("/drive/")
    @login_required
    def drive_page():
        """Renders the Zentra Drive HTML page."""
        return render_template("drive.html")

    # ─── LIST ──────────────────────────────────────────────────────────────────

    @app.route("/drive/api/list")
    @login_required
    def drive_list():
        """
        GET /drive/api/list?path=<relative_path>
        Returns JSON list of files and folders.
        """
        root = plugin.get_root()
        rel = request.args.get("path", "")
        target = _safe_path(root, rel)

        if target is None:
            return jsonify({"ok": False, "error": "Path non consentito (traversal)."}), 403

        if not os.path.isdir(target):
            return jsonify({"ok": False, "error": "Percorso non trovato."}), 404

        try:
            entries = []
            for name in sorted(os.listdir(target)):
                full = os.path.join(target, name)
                rel_entry = os.path.relpath(full, root).replace("\\", "/")
                stat = os.stat(full)
                entries.append({
                    "name": name,
                    "path": rel_entry,
                    "is_dir": os.path.isdir(full),
                    "size": stat.st_size if os.path.isfile(full) else None,
                    "modified": int(stat.st_mtime)
                })
            
            # Build breadcrumb
            crumbs = []
            parts = os.path.relpath(target, root).replace("\\", "/").split("/")
            if parts == ["."]:
                parts = []
            cumulative = ""
            for part in parts:
                cumulative = (cumulative + "/" + part).lstrip("/")
                crumbs.append({"name": part, "path": cumulative})

            return jsonify({"ok": True, "path": rel, "entries": entries, "breadcrumb": crumbs})
        except Exception as e:
            _log.error(f"[Drive] list error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    # ─── UPLOAD ────────────────────────────────────────────────────────────────

    @app.route("/drive/api/upload", methods=["POST"])
    @login_required
    def drive_upload():
        """
        POST /drive/api/upload
        Form: files[] + path (target directory, relative)
        """
        root = plugin.get_root()
        rel = request.form.get("path", "")
        target_dir = _safe_path(root, rel)

        if target_dir is None:
            return jsonify({"ok": False, "error": "Path non consentito."}), 403
        if not os.path.isdir(target_dir):
            return jsonify({"ok": False, "error": "Destinazione non trovata."}), 404

        allowed = plugin.get_allowed_extensions()
        max_bytes = plugin.get_max_upload_bytes()
        uploaded = []

        files = request.files.getlist("files[]")
        if not files:
            return jsonify({"ok": False, "error": "Nessun file ricevuto."}), 400

        for f in files:
            fname = os.path.basename(f.filename or "")
            if not fname:
                continue
            
            ext = fname.rsplit(".", 1)[-1].lower() if "." in fname else ""
            if allowed and ext not in allowed:
                return jsonify({"ok": False, "error": f"Estensione '{ext}' non consentita."}), 415

            dest = os.path.join(target_dir, fname)
            # Stream read to check size without loading fully into RAM
            chunk_size = 64 * 1024
            total = 0
            with open(dest, "wb") as out:
                while True:
                    chunk = f.stream.read(chunk_size)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > max_bytes:
                        out.close()
                        os.remove(dest)
                        return jsonify({"ok": False, "error": f"File troppo grande (max {max_bytes // (1024*1024)} MB)."}), 413
                    out.write(chunk)

            _log.info(f"[Drive] Upload: {dest} ({total} bytes) by {current_user.username}")
            uploaded.append(fname)

        return jsonify({"ok": True, "uploaded": uploaded})

    # ─── DOWNLOAD ──────────────────────────────────────────────────────────────

    @app.route("/drive/api/download")
    @login_required
    def drive_download():
        """
        GET /drive/api/download?path=<relative_path>
        Returns the file as an attachment.
        """
        root = plugin.get_root()
        rel = request.args.get("path", "")
        target = _safe_path(root, rel)

        if target is None:
            abort(403)
        if not os.path.isfile(target):
            abort(404)

        _log.info(f"[Drive] Download: {target} by {current_user.username}")
        return send_file(target, as_attachment=True)

    # ─── DELETE ────────────────────────────────────────────────────────────────

    @app.route("/drive/api/delete", methods=["DELETE"])
    @login_required
    def drive_delete():
        """
        DELETE /drive/api/delete?path=<relative_path>
        Removes a file or an empty directory.
        """
        root = plugin.get_root()
        rel = request.args.get("path", "")
        target = _safe_path(root, rel)

        if target is None:
            return jsonify({"ok": False, "error": "Path non consentito."}), 403
        if not os.path.exists(target):
            return jsonify({"ok": False, "error": "Elemento non trovato."}), 404

        # Extra safety: can't delete the root itself
        if os.path.abspath(target) == os.path.abspath(root):
            return jsonify({"ok": False, "error": "Non puoi eliminare la root del Drive."}), 403

        try:
            if os.path.isdir(target):
                shutil.rmtree(target)
            else:
                os.remove(target)
            _log.info(f"[Drive] Delete: {target} by {current_user.username}")
            return jsonify({"ok": True})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    # ─── MKDIR ─────────────────────────────────────────────────────────────────

    @app.route("/drive/api/mkdir", methods=["POST"])
    @login_required
    def drive_mkdir():
        """
        POST /drive/api/mkdir
        JSON body: {"path": "<parent_rel>", "name": "<folder_name>"}
        Creates a new subdirectory.
        """
        root = plugin.get_root()
        data = request.get_json(force=True) or {}
        parent_rel = data.get("path", "")
        name = os.path.basename(data.get("name", "").strip())

        if not name:
            return jsonify({"ok": False, "error": "Nome cartella non valido."}), 400

        parent = _safe_path(root, parent_rel)
        if parent is None:
            return jsonify({"ok": False, "error": "Path non consentito."}), 403

        new_dir = _safe_path(root, os.path.join(parent_rel, name))
        if new_dir is None:
            return jsonify({"ok": False, "error": "Path non consentito."}), 403

        try:
            os.makedirs(new_dir, exist_ok=True)
            _log.info(f"[Drive] Mkdir: {new_dir} by {current_user.username}")
            return jsonify({"ok": True})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500
