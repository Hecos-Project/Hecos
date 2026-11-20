"""
hecos/modules/web_ui/chat_search/routes.py
─────────────────────────────────────────────────────────────────────────────
Flask Blueprint for Hecos Chat Search.
Completely isolated from routes_history.py.
Endpoints:
  - GET  /api/chat/search          → Search active (or explicitly archived) chats
  - POST /api/chat/search/reindex  → Rebuild user's FTS5 search index on demand
─────────────────────────────────────────────────────────────────────────────
"""
from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from hecos.core.logging import logger
from .engine import ensure_fts_index, search_chats

chat_search_bp = Blueprint("chat_search", __name__)


def _current_uid() -> str:
    try:
        if current_user and current_user.is_authenticated and getattr(current_user, "username", None):
            return current_user.username
    except Exception:
        pass
    return "admin"


@chat_search_bp.route("/api/chat/search", methods=["GET"])
@login_required
def api_chat_search():
    """
    Query parameters:
      q           : search query text (required)
      scope       : 'all' (default) | 'current'
      session_id  : current session id (used when scope='current')
      archived    : '1' ONLY when user is explicitly inside Archive Mode (default '0')
      role        : 'all' (default) | 'user' | 'assistant'
      date        : 'all' (default) | 'today' | '7d' | '30d'
      limit       : max groups/hits (default 60)
    """
    try:
        q = (request.args.get("q") or "").strip()
        scope = (request.args.get("scope") or "all").strip().lower()
        session_id = (request.args.get("session_id") or "").strip() or None
        archived = request.args.get("archived", "0") in ("1", "true", "yes")
        role_filter = (request.args.get("role") or "all").strip().lower()
        date_range = (request.args.get("date") or "all").strip().lower()
        try:
            limit = int(request.args.get("limit", 60))
        except (TypeError, ValueError):
            limit = 60

        result = search_chats(
            query=q,
            user_id=_current_uid(),
            scope=scope,
            session_id=session_id,
            archived=archived,
            role_filter=role_filter,
            date_range=date_range,
            limit=limit,
        )
        resp = jsonify(result)
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return resp
    except Exception as e:
        logger.error(f"[CHAT_SEARCH] /api/chat/search error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


@chat_search_bp.route("/api/chat/search/reindex", methods=["POST"])
@login_required
def api_chat_search_reindex():
    """Rebuilds the FTS5 index for the authenticated user's chat vault."""
    try:
        from hecos.memory.brain_interface import _db_path
        db_path = _db_path(_current_uid())
        ok = ensure_fts_index(db_path, force_rebuild=True)
        return jsonify({"ok": bool(ok)})
    except Exception as e:
        logger.error(f"[CHAT_SEARCH] /api/chat/search/reindex error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500
