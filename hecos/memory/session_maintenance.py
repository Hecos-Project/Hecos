"""
hecos/memory/session_maintenance.py
Maintenance tasks for session management (cleanup, archiving, history limiting).
"""
import sqlite3
from datetime import datetime
from hecos.core.logging import logger
from hecos.memory.session_state import PATH_DB, _ram_sessions
from hecos.memory.session_db import _purge_vault_sessions


def delete_all_sessions(include_archived: bool = False) -> bool:
    """Deletes all ACTIVE sessions (archived are protected unless explicitly selected)."""
    _ram_sessions.clear()
    try:
        conn = sqlite3.connect(PATH_DB)
        cur  = conn.cursor()
        
        if include_archived:
            cur.execute("SELECT id FROM sessions")
        else:
            cur.execute("SELECT id FROM sessions WHERE is_archived = 0")
        active_ids = [r[0] for r in cur.fetchall()]
        if active_ids:
            holders = ",".join("?" for _ in active_ids)
            cur.execute(f"DELETE FROM history WHERE session_id IN ({holders})", active_ids)
            cur.execute(f"DELETE FROM sessions WHERE id IN ({holders})", active_ids)
        
        conn.commit()
        conn.close()

        if active_ids:
            _purge_vault_sessions(active_ids)

        conn2 = sqlite3.connect(PATH_DB)
        conn2.execute("VACUUM")
        conn2.close()
        logger.info("[SESSION] Deleted all active sessions (RAM & DB)")
        return True
    except Exception as e:
        logger.error(f"[SESSION] delete_all_sessions error: {e}")
        return False


def archive_all_sessions() -> bool:
    """Marks all non-RAM normal sessions as archived."""
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = sqlite3.connect(PATH_DB)
        cur  = conn.cursor()
        cur.execute("UPDATE sessions SET is_archived = 1, updated_at = ? WHERE is_archived = 0 AND privacy_mode = 'normal'", (now,))
        conn.commit()
        conn.close()
        logger.info("[SESSION] Archived all active DB sessions")
        return True
    except Exception as e:
        logger.error(f"[SESSION] archive_all_sessions error: {e}")
        return False


def delete_all_archived_sessions() -> bool:
    """Deletes only sessions that are currently marked as archived."""
    try:
        conn = sqlite3.connect(PATH_DB)
        cur  = conn.cursor()
        cur.execute("SELECT id FROM sessions WHERE is_archived = 1")
        archived_ids = [r[0] for r in cur.fetchall()]
        if not archived_ids:
            return True
        placeholders = ",".join("?" for _ in archived_ids)
        cur.execute(f"DELETE FROM history WHERE session_id IN ({placeholders})", archived_ids)
        cur.execute(f"DELETE FROM sessions WHERE id IN ({placeholders})", archived_ids)
        conn.commit()
        conn.close()
        _purge_vault_sessions(archived_ids)
        conn2 = sqlite3.connect(PATH_DB)
        conn2.execute("VACUUM")
        conn2.close()
        logger.info(f"[SESSION] Deleted {len(archived_ids)} archived DB sessions")
        return True
    except Exception as e:
        logger.error(f"[SESSION] delete_all_archived_sessions error: {e}")
        return False


def wipe_session_messages(session_id: str) -> bool:
    """
    Wipes messages from a session.
    For RAM sessions: clears the messages list.
    For DB sessions: deletes history rows.
    """
    if session_id in _ram_sessions:
        _ram_sessions[session_id]["messages"] = []
        logger.info(f"[SESSION] Wiped RAM messages for session {session_id}")
        return True
    try:
        conn = sqlite3.connect(PATH_DB)
        cur  = conn.cursor()
        cur.execute("DELETE FROM history WHERE session_id = ?", (session_id,))
        conn.commit()
        conn.close()
        logger.info(f"[SESSION] Wiped DB messages for session {session_id}")
        return True
    except Exception as e:
        logger.error(f"[SESSION] wipe_session_messages error: {e}")
        return False


def auto_limit_history(user_id: str = "admin", max_messages: int = 2000):
    """Trims the user's chat history to the most recent `max_messages` rows."""
    try:
        from hecos.memory.brain_interface import _db_path
        db = _db_path(user_id)
        with sqlite3.connect(db, timeout=10) as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM history")
            total = cur.fetchone()[0]
            if total > max_messages:
                excess = total - max_messages
                cur.execute(
                    "DELETE FROM history WHERE id IN "
                    "(SELECT id FROM history ORDER BY id ASC LIMIT ?)",
                    (excess,)
                )
                conn.commit()
                logger.debug(f"[SESSION] auto_limit_history: trimmed {excess} old rows for '{user_id}'")
    except Exception as e:
        logger.debug(f"[SESSION] auto_limit_history error (non-critical): {e}")
