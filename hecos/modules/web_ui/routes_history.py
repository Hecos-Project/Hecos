"""
MODULE: Chat History Routes
DESCRIPTION: Flask blueprint for managing named chat sessions.
             Provides CRUD API for session list, messages, rename, delete, wipe.
"""

from flask import Blueprint, jsonify, request
from hecos.core.logging import logger

history_bp = Blueprint("history", __name__)


def _sm():
    """Lazy-load session_manager to avoid circular imports."""
    from hecos.memory import session_manager
    return session_manager


def _pm():
    """Lazy-load privacy_manager."""
    from hecos.core.privacy import privacy_manager
    return privacy_manager


# ──────────────────────────────────────────────────────────────────────────────
# SESSION ENDPOINTS
# ──────────────────────────────────────────────────────────────────────────────

@history_bp.route("/api/chat/sessions", methods=["GET"])
def list_sessions():
    """Returns all saved chat sessions."""
    try:
        show_archived = request.args.get("archived", "0") == "1"
        sessions = _sm().get_sessions(include_archived=show_archived)
        return jsonify({"ok": True, "sessions": sessions})
    except Exception as e:
        logger.error(f"[HISTORY] list_sessions error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


@history_bp.route("/api/chat/sessions", methods=["POST"])
def create_session():
    """Creates a new chat session. Body: {title?, privacy_mode?}"""
    try:
        data = request.get_json(silent=True) or {}
        title        = data.get("title")
        privacy_mode = data.get("privacy_mode", "normal")
        
        session_id = _sm().create_session(title=title, privacy_mode=privacy_mode)
        # Set the new session as active in the privacy manager
        _pm().set_session(session_id, privacy_mode)
        
        return jsonify({"ok": True, "session_id": session_id})
    except Exception as e:
        logger.error(f"[HISTORY] create_session error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


@history_bp.route("/api/chat/sessions/active", methods=["GET"])
def get_active_session():
    """Returns the currently active session ID and mode."""
    try:
        pm = _pm()
        return jsonify({
            "ok": True,
            "session_id": pm.get_session_id(),
            "mode": pm.get_mode()
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@history_bp.route("/api/chat/sessions/active", methods=["POST"])
def set_active_session():
    """Activates an existing session. Body: {session_id, privacy_mode?}"""
    try:
        data = request.get_json(silent=True) or {}
        session_id   = data.get("session_id")
        if not session_id:
            return jsonify({"ok": False, "error": "session_id required"}), 400
        
        session = _sm().get_session(session_id)
        if not session:
            return jsonify({"ok": False, "error": "Session not found"}), 404
        
        mode = data.get("privacy_mode", session.get("privacy_mode", "normal"))
        _pm().set_session(session_id, mode)
        return jsonify({"ok": True, "session_id": session_id, "mode": mode})
    except Exception as e:
        logger.error(f"[HISTORY] set_active_session error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


@history_bp.route("/api/chat/sessions/<session_id>/messages", methods=["GET"])
def get_session_messages(session_id):
    """Returns all messages for a given session."""
    try:
        messages = _sm().get_session_messages(session_id)
        return jsonify({"ok": True, "messages": messages, "count": len(messages)})
    except Exception as e:
        logger.error(f"[HISTORY] get_session_messages error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


@history_bp.route("/api/chat/sessions/<session_id>", methods=["PATCH"])
def rename_session(session_id):
    """Renames a session. Body: {title}"""
    try:
        data = request.get_json(silent=True) or {}
        new_title = data.get("title", "").strip()
        if not new_title:
            return jsonify({"ok": False, "error": "title required"}), 400
        ok = _sm().rename_session(session_id, new_title)
        return jsonify({"ok": ok})
    except Exception as e:
        logger.error(f"[HISTORY] rename_session error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


@history_bp.route("/api/chat/sessions/all", methods=["DELETE"])
def delete_all_sessions():
    """Deletes all sessions completely."""
    try:
        ok = _sm().delete_all_sessions()
        return jsonify({"ok": ok})
    except Exception as e:
        logger.error(f"[HISTORY] delete_all_sessions error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


@history_bp.route("/api/chat/sessions/<session_id>/archive", methods=["POST"])
def archive_session(session_id):
    """Archives or restores a session. Body: {archived: bool}"""
    try:
        data = request.get_json(silent=True) or {}
        state = data.get("archived", True)
        ok = _sm().archive_session(session_id, archived=state)
        return jsonify({"ok": ok})
    except Exception as e:
        logger.error(f"[HISTORY] archive_session error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


@history_bp.route("/api/chat/sessions/<session_id>", methods=["DELETE"])
def delete_session(session_id):
    """Deletes a session and all its messages."""
    try:
        ok = _sm().delete_session(session_id)
        return jsonify({"ok": ok})
    except Exception as e:
        logger.error(f"[HISTORY] delete_session error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


@history_bp.route("/api/chat/sessions/<session_id>/wipe", methods=["POST"])
def wipe_session(session_id):
    """Wipes messages from a session (auto-wipe mode). Keeps session entry."""
    try:
        ok = _sm().wipe_session_messages(session_id)
        return jsonify({"ok": ok})
    except Exception as e:
        logger.error(f"[HISTORY] wipe_session error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


# ──────────────────────────────────────────────────────────────────────────────
# PRIVACY MODE ENDPOINT
# ──────────────────────────────────────────────────────────────────────────────

@history_bp.route("/api/chat/privacy", methods=["GET"])
def get_privacy():
    """Returns current privacy mode for the active session."""
    try:
        pm = _pm()
        return jsonify({
            "ok": True,
            "mode": pm.get_mode(),
            "is_incognito": pm.is_incognito(),
            "is_auto_wipe": pm.is_auto_wipe(),
            "session_id": pm.get_session_id()
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@history_bp.route("/api/chat/privacy", methods=["POST"])
def set_privacy():
    """Sets the privacy mode for the current session. Body: {mode}"""
    try:
        data = request.get_json(silent=True) or {}
        mode = data.get("mode", "normal")
        if mode not in ("normal", "auto_wipe", "incognito"):
            return jsonify({"ok": False, "error": "Invalid mode"}), 400
        pm = _pm()
        session_id = pm.get_session_id() or "default"
        
        # 1. Instruct session_manager to move it between DB/RAM if necessary
        if session_id != "default":
            _sm().change_session_mode(session_id, mode)
            
        # 2. Update privacy tracking
        pm.set_session(session_id, mode)
        return jsonify({"ok": True, "mode": mode})
    except Exception as e:
        logger.error(f"[HISTORY] set_privacy error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


@history_bp.route("/api/chat/sessions/wipe-all", methods=["POST"])
def wipe_all_sessions():
    """Deletes ALL sessions and their messages."""
    try:
        sessions = _sm().get_sessions()
        for s in sessions:
            _sm().delete_session(s["id"])
        return jsonify({"ok": True, "deleted": len(sessions)})
    except Exception as e:
        logger.error(f"[HISTORY] wipe_all_sessions error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


@history_bp.route("/api/chat/sessions/wipe-old", methods=["POST"])
def wipe_old_sessions():
    """Deletes messages older than N days (via memory clear_history)."""
    try:
        days = int(request.args.get("days", 30))
        from hecos.memory import clear_history
        ok = clear_history(days=days)
        return jsonify({"ok": ok})
    except Exception as e:
        logger.error(f"[HISTORY] wipe_old_sessions error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500
