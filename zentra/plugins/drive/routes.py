"""
Plugin: Zentra Drive — Routes
REST API for the HTTP File Manager.
All routes require authentication.
"""

import os
import shutil
from flask import request, jsonify, send_file, render_template, abort, Blueprint
from flask_login import login_required, current_user
from zentra.core.logging import logger

# Declare the Drive Blueprint
# We use a unique name 'zentra_drive' to avoid internal Flask collisions
drive_bp = Blueprint(
    "zentra_drive", 
    __name__, 
    template_folder="templates",
    static_folder="static",
    static_url_path="/drive_static"
)


def _get_quick_links(root_dir: str) -> list:
    """
    Scans well-known Zentra directories and returns a list of groups,
    each with a title, icon, and a list of {name, path} items.
    """
    SCAN_GROUPS = [
        {
            "id":    "system",
            "title": "⚙️ System Config",
            "dirs":  ["zentra/config/data"],
            "exts":  {".yaml", ".yml", ".json"},
            "exclude": {".example"}, 
        },
        {
            "id":    "souls",
            "title": "🧠 Personality Souls",
            "dirs":  ["zentra/personality"],
            "exts":  {".yaml", ".yml"},
        },
        {
            "id":    "rp_chars",
            "title": "🎭 Roleplay Characters",
            "dirs":  ["zentra/plugins/roleplay/characters"],
            "exts":  {".yaml", ".yml", ".json"},
        },
        {
            "id":    "rp_scenes",
            "title": "🎬 Roleplay Scenes",
            "dirs":  ["zentra/plugins/roleplay/scenes"],
            "exts":  {".yaml", ".yml", ".json"},
        },
        {
            "id":    "routing",
            "title": "🔀 Routing & Overrides",
            "dirs":  ["zentra/config"],
            "exts":  {".yaml", ".yml"},
            "recursive": False, 
        },
    ]

    groups = []
    for grp in SCAN_GROUPS:
        items = []
        exclude_suffixes = grp.get("exclude", set())
        recursive = grp.get("recursive", True)

        for rel_dir in grp["dirs"]:
            abs_dir = os.path.normpath(os.path.join(root_dir, rel_dir))
            if not os.path.isdir(abs_dir):
                continue

            walk_iter = os.walk(abs_dir) if recursive else [(abs_dir, [], os.listdir(abs_dir))]
            for dirpath, _, filenames in walk_iter:
                for fname in sorted(filenames):
                    ext = os.path.splitext(fname)[1].lower()
                    if ext not in grp["exts"]:
                        continue
                    if any(fname.endswith(s) for s in exclude_suffixes):
                        continue
                    abs_file = os.path.join(dirpath, fname).replace("\\", "/")
                    items.append({"name": fname, "path": abs_file})

        if items:
            groups.append({"id": grp["id"], "title": grp["title"], "items": items})

    return groups


def _safe_path(root: str, rel_path: str) -> str | None:
    """
    Resolves a relative path against the drive root, OR accepts an absolute path 
    directly to allow navigating across different disks (e.g., D:\)
    Returns None if malicious path traversal is detected.
    """
    import sys

    # If the provided path is already absolute (e.g., "D:\folder" or "/mnt")
    if os.path.isabs(rel_path) or (sys.platform == "win32" and ":" in rel_path):
        candidate = os.path.abspath(os.path.normpath(rel_path))
        drive_root = os.path.splitdrive(candidate)[0] + os.sep
        # Prevent traversal above the physical drive root
        if not candidate.startswith(drive_root):
            return None
        return candidate

    # Otherwise, resolve against the configured default root
    candidate = os.path.normpath(os.path.join(root, rel_path.lstrip("/\\")))
    candidate = os.path.abspath(candidate)
    root_abs = os.path.abspath(root)
    
    # Security: path must start with root
    if not candidate.startswith(root_abs):
        return None
    return candidate


def init_drive_routes(app, logger_instance=None):
    """Registers the /drive blueprint on the Flask app."""
    _log = logger_instance or logger
    _log.info("[Drive] Initializing Drive routes...")

    # ─── Load Extensions ────────────────────────────────────────────────────────
    try:
        from zentra.core.system.extension_loader import load_extension_routes, discover_extensions
        plugin_dir = os.path.dirname(os.path.abspath(__file__))
        discover_extensions("DRIVE", plugin_dir)
        load_extension_routes(app, "DRIVE", "editor")
    except Exception as _ext_err:
        import traceback
        tb_str = traceback.format_exc()
        try:
            with open("C:\\Zentra-Core\\drive_editor_crash.txt", "w") as f:
                f.write(f"ERROR: {_ext_err}\n{tb_str}")
        except: pass
        _log.error(f"[Drive] Failed to load editor extension: {_ext_err}\n{tb_str}")

    # ─── Register Drive Blueprint ──────────────────────────────────────────────
    if "zentra_drive" not in app.blueprints:
        app.register_blueprint(drive_bp)
        _log.info(f"[Drive] Blueprint 'zentra_drive' registered (Prefix: {drive_bp.url_prefix or '/'})")
    else:
        _log.debug("[Drive] Blueprint 'zentra_drive' already registered.")




# ─── PAGE ──────────────────────────────────────────────────────────────────

@drive_bp.route("/drive")
@drive_bp.route("/drive/")
@login_required
def drive_page():
    """Renders the Zentra Drive HTML page."""
    return render_template("drive.html")


# ─── QUICK LINKS ───────────────────────────────────────────────────────────

@drive_bp.route("/drive/api/quick_links")
@login_required
def drive_quick_links():
    """Returns JSON list of system quick links."""
    # We use the Zentra project root for scanning system files.
    # routes.py is in zentra/plugins/drive/ - we need to go up 3 levels.
    _dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(_dir)))
    links = _get_quick_links(project_root)
    return jsonify({"ok": True, "groups": links})


# ─── LIST ──────────────────────────────────────────────────────────────────

@drive_bp.route("/drive/api/list")
@login_required
def drive_list():
    """Returns JSON list of files and folders."""
    from .main import get_plugin
    plugin = get_plugin()
    root = plugin.get_root()
    rel = request.args.get("path", "")
    target = _safe_path(root, rel)

    if target is None:
        return jsonify({"ok": False, "error": "Forbidden path (traversal)."}), 403
    if not os.path.isdir(target):
        return jsonify({"ok": False, "error": "Path not found."}), 404

    try:
        entries = []
        for name in sorted(os.listdir(target)):
            full = os.path.join(target, name)
            try:
                rel_entry = os.path.relpath(full, root).replace("\\", "/")
            except ValueError:
                rel_entry = full.replace("\\", "/")
            
            stat = os.stat(full)
            entries.append({
                "name": name,
                "path": rel_entry,
                "is_dir": os.path.isdir(full),
                "size": stat.st_size if os.path.isfile(full) else None,
                "modified": int(stat.st_mtime)
            })
        
        abs_target = os.path.abspath(target).replace("\\", "/")
        import sys
        if sys.platform == "win32":
            slash_parts = abs_target.split("/")
            root_display = slash_parts[0] + "/"
            parts = [p for p in slash_parts[1:] if p]
        else:
            parts = [p for p in abs_target.split("/") if p]
            root_display = "/"

        crumbs = []
        cumulative = root_display.rstrip("/") if sys.platform == "win32" else ""
        for part in parts:
            cumulative += "/" + part
            crumbs.append({"name": part, "path": cumulative, "abs": cumulative})

        return jsonify({
            "ok": True, "path": rel, "abs_path": abs_target,
            "root_label": root_display, "entries": entries, "breadcrumb": crumbs
        })
    except Exception as e:
        logger.error(f"[Drive] List error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


# ─── UPLOAD ────────────────────────────────────────────────────────────────

@drive_bp.route("/drive/api/upload", methods=["POST"])
@login_required
def drive_upload():
    """POST /drive/api/upload"""
    from .main import get_plugin
    plugin = get_plugin()
    root = plugin.get_root()
    rel = request.form.get("path", "")
    target_dir = _safe_path(root, rel)

    if target_dir is None:
        return jsonify({"ok": False, "error": "Forbidden path."}), 403
    if not os.path.isdir(target_dir):
        return jsonify({"ok": False, "error": "Destination not found."}), 404

    allowed = plugin.get_allowed_extensions()
    max_bytes = plugin.get_max_upload_bytes()
    uploaded = []

    files = request.files.getlist("files[]")
    if not files:
        return jsonify({"ok": False, "error": "No files received."}), 400

    for f in files:
        fname = os.path.basename(f.filename or "")
        if not fname: continue
        
        ext = fname.rsplit(".", 1)[-1].lower() if "." in fname else ""
        if allowed and ext not in allowed:
            return jsonify({"ok": False, "error": f"Extension '{ext}' forbidden."}), 415

        dest = os.path.join(target_dir, fname)
        chunk_size = 64 * 1024
        total = 0
        with open(dest, "wb") as out:
            while True:
                chunk = f.stream.read(chunk_size)
                if not chunk: break
                total += len(chunk)
                if total > max_bytes:
                    out.close()
                    os.remove(dest)
                    return jsonify({"ok": False, "error": "File too large."}), 413
                out.write(chunk)

        logger.info(f"[Drive] Upload: {dest} ({total} bytes) by {current_user.username}")
        uploaded.append(fname)

    return jsonify({"ok": True, "uploaded": uploaded})


# ─── DOWNLOAD ──────────────────────────────────────────────────────────────

@drive_bp.route("/drive/api/download")
@login_required
def drive_download():
    """GET /drive/api/download"""
    from .main import get_plugin
    plugin = get_plugin()
    root = plugin.get_root()
    rel = request.args.get("path", "")
    target = _safe_path(root, rel)

    if target is None: abort(403)
    if not os.path.isfile(target): abort(404)

    logger.info(f"[Drive] Download: {target} by {current_user.username}")
    return send_file(target, as_attachment=True)


# ─── DELETE ────────────────────────────────────────────────────────────────

@drive_bp.route("/drive/api/delete", methods=["DELETE"])
@login_required
def drive_delete():
    """DELETE /drive/api/delete"""
    from .main import get_plugin
    plugin = get_plugin()
    root = plugin.get_root()
    rel = request.args.get("path", "")
    target = _safe_path(root, rel)

    if target is None:
        return jsonify({"ok": False, "error": "Forbidden path."}), 403
    if not os.path.exists(target):
        return jsonify({"ok": False, "error": "Not found."}), 404
    if os.path.abspath(target) == os.path.abspath(root):
        return jsonify({"ok": False, "error": "Cannot delete root."}), 403

    try:
        if os.path.isdir(target):
            shutil.rmtree(target)
        else:
            os.remove(target)
        logger.info(f"[Drive] Delete: {target} by {current_user.username}")
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ─── MKDIR ─────────────────────────────────────────────────────────────────

@drive_bp.route("/drive/api/mkdir", methods=["POST"])
@login_required
def drive_mkdir():
    """POST /drive/api/mkdir"""
    from .main import get_plugin
    plugin = get_plugin()
    root = plugin.get_root()
    data = request.get_json(force=True) or {}
    parent_rel = data.get("path", "")
    name = os.path.basename(data.get("name", "").strip())

    if not name:
        return jsonify({"ok": False, "error": "Invalid name."}), 400

    parent = _safe_path(root, parent_rel)
    if parent is None:
        return jsonify({"ok": False, "error": "Forbidden path."}), 403

    new_dir = _safe_path(root, os.path.join(parent_rel, name))
    if new_dir is None:
        return jsonify({"ok": False, "error": "Forbidden path."}), 403

    try:
        os.makedirs(new_dir, exist_ok=True)
        logger.info(f"[Drive] Mkdir: {new_dir} by {current_user.username}")
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ─── DRIVES ────────────────────────────────────────────────────────────────

@drive_bp.route("/drive/api/drives")
@login_required
def drive_list_drives():
    """Returns all available drives/volumes on the server."""
    import sys
    drives = []
    try:
        if sys.platform == "win32":
            import ctypes
            bitmask = ctypes.windll.kernel32.GetLogicalDrives()
            for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                if bitmask & 1:
                    path = f"{letter}:\\"
                    if os.path.exists(path):
                        try:
                            buf = ctypes.create_unicode_buffer(256)
                            ctypes.windll.kernel32.GetVolumeInformationW(path, buf, 256, None, None, None, None, 0)
                            vol_label = buf.value or ""
                        except Exception: vol_label = ""
                        try:
                            free_bytes = shutil.disk_usage(path).free
                        except Exception: free_bytes = 0
                        drives.append({
                            "letter": letter, "label": vol_label or f"Drive {letter}:",
                            "path": path.replace("\\", "/"), "free_gb": round(free_bytes / (1024 ** 3), 1)
                        })
                bitmask >>= 1
        else:
            drives = [{"letter": "/", "label": "Root (/)", "path": "/", "free_gb": 0}]
    except Exception as e:
        logger.error(f"[Drive] Drives list error: {e}")
    return jsonify({"ok": True, "drives": drives})
