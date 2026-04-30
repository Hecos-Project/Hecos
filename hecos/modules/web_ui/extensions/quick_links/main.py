"""
Quick Links — WEB_UI Shared Extension
Backend routes for user-managed sidebar quick links.
Links are persisted in workspace/quick_links.json (per-user).
"""
import os
import json
import uuid
from hecos.core.logging import logger

# Path to the storage file (inside workspace/ which is .gitignored)
_STORAGE_BASE = None


def _get_storage_path(root_dir: str) -> str:
    """Returns the absolute path to the quick_links data file."""
    workspace_dir = os.path.join(root_dir, "workspace")
    os.makedirs(workspace_dir, exist_ok=True)
    return os.path.join(workspace_dir, "quick_links.json")


def _load_links(root_dir: str) -> list:
    """Loads the links list from disk. Returns [] on missing/corrupt file."""
    path = _get_storage_path(root_dir)
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception as e:
        logger.error(f"[QuickLinks] Failed to load links: {e}")
        return []


def _save_links(links: list, root_dir: str) -> bool:
    """Persists the links list to disk."""
    path = _get_storage_path(root_dir)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(links, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"[QuickLinks] Failed to save links: {e}")
        return False


def init_routes(app, root_dir: str = None):
    """
    Registers Quick Links CRUD API routes.
    Called by extension_loader when eager-loading this extension.
    """
    from flask import request, jsonify, send_from_directory
    from flask_login import login_required

    # Resolve root_dir from __file__ if not explicitly provided
    if root_dir is None:
        # __file__ = modules/web_ui/extensions/quick_links/main.py
        root_dir = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "..")
        )

    # ── Static assets served from this extension ────────────────────────────
    _static_dir = os.path.join(os.path.dirname(__file__), "static")

    @app.route("/ext/quick_links/static/<path:filename>")
    def quick_links_static(filename):
        return send_from_directory(_static_dir, filename)

    # ── REST API ─────────────────────────────────────────────────────────────

    @app.route("/api/ext/quick_links", methods=["GET"])
    @login_required
    def ql_get():
        """Returns the saved links JSON list."""
        links = _load_links(root_dir)
        return jsonify({"ok": True, "links": links})

    @app.route("/api/ext/quick_links", methods=["POST"])
    @login_required
    def ql_add():
        """
        Adds a new link.
        Body: { label: str, url: str, icon: str (emoji or empty), target: "_blank"|"_self" }
        """
        data = request.get_json(force=True) or {}
        label = (data.get("label") or "").strip()
        url   = (data.get("url")   or "").strip()
        icon  = (data.get("icon")  or "🔗").strip()
        target = data.get("target", "_blank")
        if target not in ("_blank", "_self"):
            target = "_blank"

        if not label or not url:
            return jsonify({"ok": False, "error": "label and url are required"}), 400

        links = _load_links(root_dir)
        new_link = {
            "id":     str(uuid.uuid4()),
            "label":  label,
            "url":    url,
            "icon":   icon,
            "target": target,
        }
        links.append(new_link)
        _save_links(links, root_dir)
        logger.debug("QuickLinks", f"Added link: {label} → {url}")
        return jsonify({"ok": True, "link": new_link})

    @app.route("/api/ext/quick_links/<link_id>", methods=["DELETE"])
    @login_required
    def ql_delete(link_id):
        """Removes the link with the given id."""
        links = _load_links(root_dir)
        before = len(links)
        links = [l for l in links if l.get("id") != link_id]
        if len(links) == before:
            return jsonify({"ok": False, "error": "Link not found"}), 404
        _save_links(links, root_dir)
        logger.debug("QuickLinks", f"Deleted link id={link_id}")
        return jsonify({"ok": True})

    @app.route("/api/ext/quick_links/reorder", methods=["POST"])
    @login_required
    def ql_reorder():
        """
        Saves a new order for links.
        Body: { ids: [id1, id2, ...] }  — full ordered list of IDs.
        """
        data = request.get_json(force=True) or {}
        ids = data.get("ids", [])
        links = _load_links(root_dir)
        id_map = {l["id"]: l for l in links}
        reordered = [id_map[i] for i in ids if i in id_map]
        _save_links(reordered, root_dir)
        return jsonify({"ok": True})

    logger.debug("QuickLinks", "Quick Links extension routes registered.")
