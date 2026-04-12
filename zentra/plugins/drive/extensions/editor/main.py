"""
Extension: Zentra Code Editor
Parent: DRIVE
Description: Serves a Monaco (VS Code) editor UI for reading and saving files in the Drive.
Routes registered: /drive/editor, /drive/api/editor/read, /drive/api/editor/save
"""

import os
from flask import request, jsonify, render_template, abort, Blueprint
from flask_login import login_required, current_user

try:
    from zentra.core.logging import logger
except ImportError:
    class _L:
        def info(self, *a): print("[EDITOR]", *a)
        def error(self, *a): print("[EDITOR ERR]", *a)
        def debug(self, *a, **kw): pass
    logger = _L()

# Declare the Editor Blueprint
# We use a unique name 'zentra_editor' to avoid internal Flask collisions
editor_bp = Blueprint(
    "zentra_editor", 
    __name__, 
    template_folder="templates",
    static_folder="static",
    static_url_path="/editor_static"
)

# === Constants ===
# File extensions that Monaco can provide syntax highlighting for
EDITABLE_EXTENSIONS = {
    ".py", ".js", ".ts", ".json", ".yaml", ".yml", ".toml",
    ".html", ".htm", ".css", ".scss", ".sh", ".bat", ".ps1",
    ".md", ".txt", ".ini", ".cfg", ".conf", ".log",
    ".xml", ".csv", ".env"
}

# Map extension → Monaco language ID
LANG_MAP = {
    ".py": "python",   ".js": "javascript",  ".ts": "typescript",
    ".json": "json",   ".yaml": "yaml",       ".yml": "yaml",
    ".toml": "ini",    ".html": "html",       ".htm": "html",
    ".css": "css",     ".scss": "scss",       ".sh": "shell",
    ".bat": "bat",     ".ps1": "powershell",  ".md": "markdown",
    ".txt": "plaintext", ".ini": "ini",       ".cfg": "ini",
    ".conf": "ini",    ".log": "plaintext",   ".xml": "xml",
    ".csv": "plaintext", ".env": "plaintext",
}


def _get_config() -> dict:
    """Reads editor config from ConfigManager, falling back to manifest defaults."""
    defaults = {
        "enabled": True, # Added enabled flag
        "max_file_size_kb": 1024,
        "theme": "vs-dark",
        "word_wrap": True,
        "spell_check": False,
    }
    try:
        from app.config import ConfigManager
        cfg = ConfigManager()
        conf = cfg.config.get("plugins", {}).get("DRIVE", {}).get("editor", {})
        for k, v in conf.items():
            if k in defaults:
                defaults[k] = v
    except Exception:
        pass
    return defaults


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
            "exclude": {".example"},  # skip *.example files
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
            "recursive": False,  # only top-level files in that extra dir
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
                    # Skip excluded suffixes (e.g., ".example")
                    if any(fname.endswith(s) for s in exclude_suffixes):
                        continue
                    abs_file = os.path.join(dirpath, fname)
                    # Build a path relative to root_dir, using forward slashes for URLs
                    rel_path = os.path.relpath(abs_file, root_dir).replace("\\", "/")
                    items.append({"name": fname, "path": rel_path})

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
    # If the provided path is already absolute (e.g., "C:\Zentra-Core\main.py")
    if os.path.isabs(rel_path) or (sys.platform == "win32" and ":" in rel_path):
        candidate = os.path.abspath(os.path.normpath(rel_path))
        drive_root = os.path.splitdrive(candidate)[0] + os.sep
        if not candidate.startswith(drive_root):
            return None
        return candidate

    # Relative path logic
    candidate = os.path.normpath(os.path.join(root, rel_path.lstrip("/\\")))
    candidate = os.path.abspath(candidate)
    root_abs = os.path.abspath(root)
    if not candidate.startswith(root_abs):
        return None
    return candidate


def _get_drive_root() -> str:
    """Gets the Drive root folder, defaulting to C:\ on Windows if not set."""
    try:
        from app.config import ConfigManager
        cfg = ConfigManager()
        root = cfg.get_plugin_config("DRIVE", "root_dir", "")
    except Exception:
        root = ""
    
    if not root:
        import sys
        root = "C:\\" if sys.platform == "win32" else "/"
        
    return os.path.abspath(root)


def init_routes(app):
    """Register editor routes on the Flask app."""
    cfg = _get_config()
    if not cfg.get("enabled", True):
        logger.info("[Editor] Extension disabled in config. Skipping route registration.")
        return

    if "zentra_editor" not in app.blueprints:
        app.register_blueprint(editor_bp)
        logger.info("[Editor] Blueprint 'zentra_editor' registered.")


# ─── ROUTES ──────────────────────────────────────────────────────────────────

@editor_bp.route("/drive/editor")
@login_required
def drive_editor_page():
    """Renders the Monaco Code Editor page for a given file."""
    rel = request.args.get("path", "")
    if not rel:
        abort(400)

    root = _get_drive_root()
    target = _safe_path(root, rel)

    if target is None:
        abort(403)
    if not os.path.isfile(target):
        abort(404)

    ext = os.path.splitext(target)[1].lower()
    if ext not in EDITABLE_EXTENSIONS:
        abort(415)  # Unsupported media type

    cfg = _get_config()
    lang = LANG_MAP.get(ext, "plaintext")
    filename = os.path.basename(target)

    # Scan Zentra root for known config dirs to populate the sidebar
    zentra_root = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".."))
    quick_links = _get_quick_links(zentra_root)

    return render_template(
        "editor.html",
        file_path=rel,
        filename=filename,
        language=lang,
        theme=cfg["theme"],
        word_wrap="on" if cfg["word_wrap"] else "off",
        spell_check=cfg["spell_check"],
        quick_links=quick_links,
    )

@editor_bp.route("/drive/api/editor/read")
@login_required
def drive_editor_read():
    """
    GET /drive/api/editor/read?path=<rel>
    Returns file content as JSON for the Monaco editor to load.
    """
    rel = request.args.get("path", "")
    root = _get_drive_root()
    target = _safe_path(root, rel)

    if target is None:
        return jsonify({"ok": False, "error": "Path not allowed."}), 403
    if not os.path.isfile(target):
        return jsonify({"ok": False, "error": "File not found."}), 404

    cfg = _get_config()
    max_bytes = cfg["max_file_size_kb"] * 1024
    size = os.path.getsize(target)

    if size > max_bytes:
        return jsonify({
            "ok": False,
            "error": f"File too large ({size // 1024} KB). Limit is {cfg['max_file_size_kb']} KB."
        }), 413

    try:
        with open(target, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        ext = os.path.splitext(target)[1].lower()
        lang = LANG_MAP.get(ext, "plaintext")

        return jsonify({
            "ok": True,
            "content": content,
            "language": lang,
            "size_kb": round(size / 1024, 1),
        })
    except Exception as e:
        logger.error(f"[Editor] read error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500

@editor_bp.route("/drive/api/editor/save", methods=["POST"])
@login_required
def drive_editor_save():
    """
    POST /drive/api/editor/save
    JSON body: {"path": "<rel>", "content": "<new content>"}
    Writes the modified content back to disk atomically.
    """
    data = request.get_json(force=True) or {}
    rel = data.get("path", "")
    content = data.get("content", "")

    root = _get_drive_root()
    target = _safe_path(root, rel)

    if target is None:
        return jsonify({"ok": False, "error": "Path not allowed."}), 403
    if not os.path.isfile(target):
        return jsonify({"ok": False, "error": "File not found."}), 404

    ext = os.path.splitext(target)[1].lower()
    if ext not in EDITABLE_EXTENSIONS:
        return jsonify({"ok": False, "error": "File type not editable."}), 415

    cfg = _get_config()
    if len(content.encode("utf-8")) > cfg["max_file_size_kb"] * 1024:
        return jsonify({"ok": False, "error": "Content exceeds maximum file size limit."}), 413

    try:
        # Atomic write: write to temp then rename
        temp_path = target + ".zentra_editor_tmp"
        with open(temp_path, "w", encoding="utf-8", newline="") as f:
            f.write(content)
        os.replace(temp_path, target)

        logger.info(f"[Editor] Saved: {target} by {current_user.username}")
        return jsonify({"ok": True, "message": "File saved successfully."})
    except Exception as e:
        logger.error(f"[Editor] save error: {e}")
        if os.path.exists(target + ".zentra_editor_tmp"):
            os.remove(target + ".zentra_editor_tmp")
        return jsonify({"ok": False, "error": str(e)}), 500
