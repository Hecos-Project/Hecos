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
        
        # Notify Presenter about new chat
        try:
            from hecos.core.events import emit
            emit("new_chat", {"session_id": session_id})
        except Exception:
            pass
        
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
    """Deletes all ACTIVE sessions completely."""
    try:
        ok = _sm().delete_all_sessions()
        return jsonify({"ok": ok})
    except Exception as e:
        logger.error(f"[HISTORY] delete_all_sessions error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


@history_bp.route("/api/chat/sessions/archive-all", methods=["POST"])
def archive_all_sessions():
    """Archives all active sessions."""
    try:
        ok = _sm().archive_all_sessions()
        return jsonify({"ok": ok})
    except Exception as e:
        logger.error(f"[HISTORY] archive_all_sessions error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


@history_bp.route("/api/chat/sessions/delete-archived", methods=["DELETE"])
def delete_all_archived_sessions():
    """Deletes completely all ARCHIVED sessions."""
    try:
        ok = _sm().delete_all_archived_sessions()
        return jsonify({"ok": ok})
    except Exception as e:
        logger.error(f"[HISTORY] delete_all_archived_sessions error: {e}")
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


# ──────────────────────────────────────────────────────────────────────────────
# CHAT HISTORY BACKUP / RESTORE
# ──────────────────────────────────────────────────────────────────────────────

@history_bp.route("/api/chat/sessions/backup", methods=["GET"])
def backup_chat_history():
    """
    Exports ALL normal (persisted) sessions and their messages as a JSON backup.
    Query params:
        session_id=<id>   → export only one session (optional)
    """
    from datetime import datetime, timezone
    try:
        sm = _sm()
        sid = request.args.get("session_id")

        if sid:
            # Single-session export
            session = sm.get_session(sid)
            if not session:
                return jsonify({"ok": False, "error": "Session not found"}), 404
            messages = sm.get_session_messages(sid)
            sessions_data = [{**session, "messages": messages}]
        else:
            # Full export: all active + archived normal sessions
            active   = sm.get_sessions(include_archived=False)
            archived = sm.get_sessions(include_archived=True)
            all_sessions = {s["id"]: s for s in active + archived}.values()
            sessions_data = []
            for s in all_sessions:
                msgs = sm.get_session_messages(s["id"])
                sessions_data.append({**s, "messages": msgs})

        return jsonify({
            "ok": True,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "session_count": len(sessions_data),
            "sessions": sessions_data
        })
    except Exception as e:
        logger.error(f"[HISTORY] backup_chat_history error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


@history_bp.route("/api/chat/sessions/restore", methods=["POST"])
def restore_chat_history():
    """
    Imports sessions and their messages from a JSON backup.
    Body: { sessions: [...], mode: "duplicate" | "replace" }
    mode=replace  → wipes all existing sessions first.
    mode=duplicate → appends (creates new IDs for every session).
    """
    import sqlite3, uuid as _uuid
    from datetime import datetime
    from hecos.memory.session_manager import PATH_DB, _is_ram_mode

    try:
        data = request.get_json(force=True) or {}
        sessions_payload = data.get("sessions", [])
        mode = data.get("mode", "duplicate")

        sm = _sm()

        if mode == "replace":
            sm.delete_all_sessions()

        restored_sessions = 0
        restored_messages = 0

        for s in sessions_payload:
            # Skip RAM-mode sessions from backup (they can't be restored meaningfully)
            if _is_ram_mode(s.get("privacy_mode", "normal")):
                continue

            # Always create a new ID to avoid collisions in duplicate mode
            new_sid = str(_uuid.uuid4())
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            conn = sqlite3.connect(PATH_DB)
            cur  = conn.cursor()
            cur.execute(
                "INSERT OR IGNORE INTO sessions (id, title, created_at, updated_at, privacy_mode, is_incognito, is_archived) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    new_sid,
                    s.get("title", "Restored Session"),
                    s.get("created_at", now),
                    s.get("updated_at", now),
                    "normal",
                    0,
                    int(s.get("is_archived", 0))
                )
            )
            conn.commit()
            conn.close()
            restored_sessions += 1

            # Restore messages into the per-user vault DB
            try:
                try:
                    from flask_login import current_user
                    uid = current_user.username if current_user and current_user.is_authenticated else "admin"
                except Exception:
                    uid = "admin"

                from hecos.memory.brain_interface import _db_path
                import os
                db_path = _db_path(uid)
                if not os.path.exists(db_path):
                    continue

                with sqlite3.connect(db_path) as vconn:
                    vcur = vconn.cursor()
                    for msg in s.get("messages", []):
                        vcur.execute(
                            "INSERT INTO history (timestamp, role, message, session_id) VALUES (?, ?, ?, ?)",
                            (msg.get("timestamp", now), msg.get("role", "user"), msg.get("message", ""), new_sid)
                        )
                    vconn.commit()
                    restored_messages += len(s.get("messages", []))
            except Exception as msg_err:
                logger.error(f"[HISTORY] restore messages error for session {new_sid}: {msg_err}")

        return jsonify({
            "ok": True,
            "restored_sessions": restored_sessions,
            "restored_messages": restored_messages
        }), 201

    except Exception as e:
        logger.error(f"[HISTORY] restore_chat_history error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


# ──────────────────────────────────────────────────────────────────────────────
# SINGLE MESSAGE DELETE / EDIT (Inline Chat Actions)
# ──────────────────────────────────────────────────────────────────────────────

@history_bp.route("/api/chat/messages/delete", methods=["POST"])
def delete_single_message():
    """Deletes a single message from the active session (DB or RAM)."""
    import os
    import sqlite3
    from hecos.memory.session_state import _ram_sessions
    from hecos.memory.brain_interface import _db_path

    try:
        data = request.get_json(silent=True) or {}
        session_id = data.get("session_id") or _pm().get_session_id()
        idx = data.get("index")
        role = data.get("role")
        if role == "ai":
            role = "assistant"
        content = (data.get("content") or "").strip()

        if not session_id:
            return jsonify({"ok": False, "error": "session_id required"}), 400

        # 1. RAM session check
        if session_id in _ram_sessions:
            msgs = _ram_sessions[session_id].get("messages", [])
            if isinstance(idx, int) and 0 <= idx < len(msgs):
                msgs.pop(idx)
                return jsonify({"ok": True, "deleted": True})
            if content:
                for i in range(len(msgs) - 1, -1, -1):
                    m_role = "assistant" if msgs[i].get("role") in ("ai", "assistant") else "user"
                    if (not role or m_role == role) and (msgs[i].get("message") or "").strip() == content:
                        msgs.pop(i)
                        return jsonify({"ok": True, "deleted": True})
            return jsonify({"ok": True, "deleted": False})

        # 2. SQLite DB check
        try:
            from flask_login import current_user
            uid = current_user.username if current_user and current_user.is_authenticated else "admin"
        except Exception:
            uid = "admin"

        db_path = _db_path(uid)
        if not os.path.exists(db_path):
            return jsonify({"ok": True, "deleted": False})

        deleted = False
        with sqlite3.connect(db_path, timeout=15) as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, role, message FROM history WHERE session_id = ? ORDER BY id ASC",
                (session_id,)
            )
            rows = cur.fetchall()
            target_id = None

            if isinstance(idx, int) and 0 <= idx < len(rows):
                row_id, row_role, _ = rows[idx]
                norm_row_role = "assistant" if row_role in ("ai", "assistant") else "user"
                if not role or norm_row_role == role:
                    target_id = row_id

            if target_id is None and content:
                for row_id, row_role, row_msg in reversed(rows):
                    norm_row_role = "assistant" if row_role in ("ai", "assistant") else "user"
                    if (not role or norm_row_role == role) and (row_msg or "").strip() == content:
                        target_id = row_id
                        break

            if target_id is not None:
                cur.execute("DELETE FROM history WHERE id = ?", (target_id,))
                conn.commit()
                deleted = True

        return jsonify({"ok": True, "deleted": deleted})
    except Exception as e:
        logger.error(f"[HISTORY] delete_single_message error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


@history_bp.route("/api/chat/messages/edit", methods=["POST"])
def edit_single_message():
    """Updates the text of a single message in the active session (DB or RAM)."""
    import os
    import sqlite3
    from hecos.memory.session_state import _ram_sessions
    from hecos.memory.brain_interface import _db_path

    try:
        data = request.get_json(silent=True) or {}
        session_id = data.get("session_id") or _pm().get_session_id()
        idx = data.get("index")
        role = data.get("role")
        if role == "ai":
            role = "assistant"
        new_content = (data.get("content") or "").strip()

        if not session_id or not new_content:
            return jsonify({"ok": False, "error": "session_id and content required"}), 400

        if session_id in _ram_sessions:
            msgs = _ram_sessions[session_id].get("messages", [])
            if isinstance(idx, int) and 0 <= idx < len(msgs):
                msgs[idx]["message"] = new_content
                return jsonify({"ok": True, "updated": True})
            return jsonify({"ok": True, "updated": False})

        try:
            from flask_login import current_user
            uid = current_user.username if current_user and current_user.is_authenticated else "admin"
        except Exception:
            uid = "admin"

        db_path = _db_path(uid)
        if not os.path.exists(db_path):
            return jsonify({"ok": True, "updated": False})

        updated = False
        with sqlite3.connect(db_path, timeout=15) as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, role FROM history WHERE session_id = ? ORDER BY id ASC",
                (session_id,)
            )
            rows = cur.fetchall()
            if isinstance(idx, int) and 0 <= idx < len(rows):
                row_id, row_role = rows[idx]
                norm_row_role = "assistant" if row_role in ("ai", "assistant") else "user"
                if not role or norm_row_role == role:
                    cur.execute("UPDATE history SET message = ? WHERE id = ?", (new_content, row_id))
                    conn.commit()
                    updated = True

        return jsonify({"ok": True, "updated": updated})
    except Exception as e:
        logger.error(f"[HISTORY] edit_single_message error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


