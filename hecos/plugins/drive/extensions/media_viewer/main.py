"""
Extension: Hecos Media Viewer
Parent: DRIVE
Description: Inline thumbnails (4 size modes) and a swipeable fullscreen media
             player for all media files in a Drive folder.
Routes:
  GET /drive/api/media/view?path=<rel>            — Streams file for in-browser rendering
  GET /drive/api/media/list_media?path=<rel_dir>  — Returns sorted list of media files in folder
"""

import os
from flask import request, jsonify, send_file, abort, Blueprint
from flask_login import login_required

try:
    from hecos.core.logging import logger
except ImportError:
    class _L:
        def info(self, *a): print("[MEDIA_VIEWER]", *a)
        def error(self, *a): print("[MEDIA_VIEWER ERR]", *a)
        def debug(self, *a, **kw): pass
    logger = _L()

# ─── Blueprint ─────────────────────────────────────────────────────────────────
media_viewer_bp = Blueprint(
    "hecos_media_viewer",
    __name__,
    static_folder="static",
    static_url_path="/media_viewer_static"
)

# ─── Media types ───────────────────────────────────────────────────────────────
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg", ".avif"}
VIDEO_EXTS = {".mp4", ".webm", ".ogg", ".ogv", ".mov", ".m4v", ".mkv"}
AUDIO_EXTS = {".mp3", ".wav", ".ogg", ".oga", ".flac", ".aac", ".m4a", ".opus"}
MEDIA_EXTS = IMAGE_EXTS | VIDEO_EXTS | AUDIO_EXTS


# ─── Helpers ───────────────────────────────────────────────────────────────────

def _get_drive_root() -> str:
    try:
        from hecos.app.config import ConfigManager
        cfg = ConfigManager()
        root = cfg.config.get("plugins", {}).get("DRIVE", {}).get("root_dir", "")
    except Exception:
        root = ""
    if not root:
        import sys
        root = "C:\\" if sys.platform == "win32" else "/"
    return os.path.abspath(root)


def _safe_path(root: str, rel_path: str) -> str | None:
    """Resolves a path relative to root, or accepts an absolute path directly."""
    import sys
    if os.path.isabs(rel_path) or (sys.platform == "win32" and ":" in rel_path):
        candidate = os.path.abspath(os.path.normpath(rel_path))
        drive_root = os.path.splitdrive(candidate)[0] + os.sep
        if not candidate.startswith(drive_root):
            return None
        return candidate
    candidate = os.path.normpath(os.path.join(root, rel_path.lstrip("/\\")))
    candidate = os.path.abspath(candidate)
    root_abs = os.path.abspath(root)
    if not candidate.startswith(root_abs):
        return None
    return candidate


def _media_type(name: str) -> str:
    """Returns 'image', 'video', 'audio', or 'unknown'."""
    ext = os.path.splitext(name)[1].lower()
    if ext in IMAGE_EXTS: return "image"
    if ext in VIDEO_EXTS: return "video"
    if ext in AUDIO_EXTS: return "audio"
    return "unknown"


# ─── Routes ────────────────────────────────────────────────────────────────────

@media_viewer_bp.route("/drive/api/media/view")
@login_required
def media_view():
    """
    GET /drive/api/media/view?path=<rel>
    Streams the file without forcing download, for in-browser rendering.
    """
    root = _get_drive_root()
    rel  = request.args.get("path", "")
    target = _safe_path(root, rel)

    if target is None:
        abort(403)
    if not os.path.isfile(target):
        abort(404)

    ext = os.path.splitext(target)[1].lower()
    if ext not in MEDIA_EXTS:
        abort(415)

    return send_file(target, as_attachment=False)


@media_viewer_bp.route("/drive/api/media/list_media")
@login_required
def media_list():
    """
    GET /drive/api/media/list_media?path=<rel_dir>
    Returns sorted JSON list of all media files in that directory.
    Used by the JS player to build the playlist.
    """
    root    = _get_drive_root()
    rel_dir = request.args.get("path", "")
    target  = _safe_path(root, rel_dir)

    if target is None:
        return jsonify({"ok": False, "error": "Forbidden path."}), 403
    if not os.path.isdir(target):
        return jsonify({"ok": False, "error": "Directory not found."}), 404

    try:
        entries = []
        for name in sorted(os.listdir(target), key=lambda n: n.lower()):
            if os.path.splitext(name)[1].lower() not in MEDIA_EXTS:
                continue
            full = os.path.join(target, name)
            if not os.path.isfile(full):
                continue
            try:
                rel_entry = os.path.relpath(full, root).replace("\\", "/")
            except ValueError:
                rel_entry = full.replace("\\", "/")

            entries.append({
                "name":  name,
                "path":  rel_entry,
                "type":  _media_type(name),
                "size":  os.path.getsize(full),
            })

        logger.debug(f"[MediaViewer] list_media: {len(entries)} items in '{rel_dir}'")
        return jsonify({"ok": True, "entries": entries})

    except Exception as e:
        logger.error(f"[MediaViewer] list_media error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


# ─── Extension entry point ─────────────────────────────────────────────────────

def init_routes(app):
    """Called by the Drive extension loader to register this extension."""
    if "hecos_media_viewer" not in app.blueprints:
        app.register_blueprint(media_viewer_bp)
        logger.info("[MediaViewer] Blueprint 'hecos_media_viewer' registered.")
