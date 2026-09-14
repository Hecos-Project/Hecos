"""
hecos/memory/session_crud.py
CRUD operations for chat sessions.
"""
import sqlite3
import uuid
import os
from datetime import datetime
from hecos.core.logging import logger
from hecos.memory.session_state import PATH_DB, _ram_sessions, _is_ram_mode
from hecos.memory.session_db import _purge_vault_sessions

def create_session(title: str = None, privacy_mode: str = "normal") -> str:
    """Creates a new chat session. Normal → DB. auto_wipe/incognito → RAM only."""
    session_id = str(uuid.uuid4())
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if not title:
        title = f"Chat {datetime.now().strftime('%d/%m/%Y %H:%M')}"

    if _is_ram_mode(privacy_mode):
        _ram_sessions[session_id] = {
            "id":           session_id,
            "title":        title,
            "created_at":   now,
            "updated_at":   now,
            "privacy_mode": privacy_mode,
            "is_incognito": 1 if privacy_mode == "incognito" else 0,
            "messages":     []
        }
        logger.info(f"[SESSION] Created RAM session: {session_id} (mode={privacy_mode})")
    else:
        conn = sqlite3.connect(PATH_DB)
        cur  = conn.cursor()
        cur.execute(
            "INSERT INTO sessions (id, title, created_at, updated_at, privacy_mode, is_incognito) VALUES (?, ?, ?, ?, ?, ?)",
            (session_id, title, now, now, privacy_mode, 0)
        )
        conn.commit()
        conn.close()
        logger.info(f"[SESSION] Created DB session: {session_id} (mode={privacy_mode})")

    return session_id


def get_sessions(include_archived: bool = False) -> list:
    """Returns all sessions: DB sessions + active RAM sessions, ordered by most recent."""
    results = []

    # ── DB sessions (normal)
    try:
        conn = sqlite3.connect(PATH_DB)
        conn.row_factory = sqlite3.Row
        cur  = conn.cursor()
        
        query = """
            SELECT s.id, s.title, s.created_at, s.updated_at, s.privacy_mode, s.is_incognito, s.is_archived
            FROM sessions s
            WHERE s.privacy_mode = 'normal'
        """
        if not include_archived:
            query += " AND s.is_archived = 0 "
        else:
            query += " AND s.is_archived = 1 "
            
        query += " ORDER BY s.updated_at DESC "
        cur.execute(query)
        results = [dict(r) for r in cur.fetchall()]
        conn.close()
        
        # Hydrate message_count from the dynamic user vault
        try:
            try:
                from flask_login import current_user
                uid = current_user.username if current_user and current_user.is_authenticated else "admin"
            except Exception:
                uid = "admin"
            from hecos.memory.brain_interface import _db_path
            db = _db_path(uid)
            if os.path.exists(db):
                with sqlite3.connect(db) as user_conn:
                    user_cur = user_conn.cursor()
                    for r in results:
                        cnt = user_cur.execute(
                            "SELECT COUNT(*) FROM history WHERE session_id = ?", 
                            (r["id"],)
                        ).fetchone()[0]
                        r["message_count"] = cnt
            else:
                for r in results: r["message_count"] = 0
        except Exception as dyn_e:
            logger.error(f"[SESSION] get_sessions count hydration error: {dyn_e}")
            for r in results: r.setdefault("message_count", 0)
    except Exception as e:
        logger.error(f"[SESSION] get_sessions DB error: {e}")

    # ── RAM sessions
    ram_rows = []
    for sid, sess in _ram_sessions.items():
        ram_rows.append({
            "id":            sid,
            "title":         sess["title"],
            "created_at":    sess["created_at"],
            "updated_at":    sess["updated_at"],
            "privacy_mode":  sess["privacy_mode"],
            "is_incognito":  sess["is_incognito"],
            "is_archived":   0,
            "message_count": len(sess["messages"])
        })

    all_sessions = ram_rows + results
    all_sessions.sort(key=lambda s: s.get("updated_at", ""), reverse=True)
    return all_sessions


def get_session(session_id: str) -> dict | None:
    """Returns metadata for a single session (checks RAM first, then DB)."""
    if session_id in _ram_sessions:
        sess = _ram_sessions[session_id]
        return {
            "id":            sess["id"],
            "title":         sess["title"],
            "created_at":    sess["created_at"],
            "updated_at":    sess["updated_at"],
            "privacy_mode":  sess["privacy_mode"],
            "is_incognito":  sess["is_incognito"],
        }
    try:
        conn = sqlite3.connect(PATH_DB)
        conn.row_factory = sqlite3.Row
        cur  = conn.cursor()
        cur.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception as e:
        logger.error(f"[SESSION] get_session error: {e}")
        return None


def get_session_messages(session_id: str) -> list:
    """Returns all messages for a session (RAM if non-normal, DB if normal)."""
    if session_id in _ram_sessions:
        return list(_ram_sessions[session_id]["messages"])
    try:
        try:
            from flask_login import current_user
            uid = current_user.username if current_user and current_user.is_authenticated else "admin"
        except Exception:
            uid = "admin"
            
        from hecos.memory.brain_interface import _db_path, initialize_user_vault
        initialize_user_vault(uid)
        db = _db_path(uid)
        if not os.path.exists(db):
            return []
            
        conn = sqlite3.connect(db)
        cur  = conn.cursor()
        cur.execute(
            "SELECT id, timestamp, role, message, persona_name, audio_file, model_info FROM history WHERE session_id = ? ORDER BY id ASC",
            (session_id,)
        )
        rows = cur.fetchall()
        conn.close()
        return [{"id": r[0], "timestamp": r[1], "role": r[2], "message": r[3], "persona_name": r[4], "audio_file": r[5], "model_info": r[6] if len(r) > 6 else None} for r in rows]
    except Exception as e:
        logger.error(f"[SESSION] get_session_messages error: {e}")
        return []


def add_ram_message(session_id: str, role: str, message: str):
    """Appends a message to a RAM session's in-memory store."""
    if session_id not in _ram_sessions:
        logger.warning(f"[SESSION] add_ram_message: session {session_id} not in RAM — ignoring.")
        return
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg_id = str(uuid.uuid4())
    _ram_sessions[session_id]["messages"].append({
        "id":        msg_id,
        "timestamp": now,
        "role":      role,
        "message":   message
    })
    _ram_sessions[session_id]["updated_at"] = now
    logger.debug(f"[SESSION] RAM message added ({role}) to {session_id}")


def archive_session(session_id: str, archived: bool = True) -> bool:
    """Archives or restores a session (DB only)."""
    if session_id in _ram_sessions:
        return True
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = sqlite3.connect(PATH_DB)
        cur  = conn.cursor()
        cur.execute("UPDATE sessions SET is_archived = ?, updated_at = ? WHERE id = ?", 
                    (1 if archived else 0, now, session_id))
        conn.commit()
        conn.close()
        logger.info(f"[SESSION] {'Archived' if archived else 'Restored'} {session_id}")
        return True
    except Exception as e:
        logger.error(f"[SESSION] archive_session error: {e}")
        return False


def rename_session(session_id: str, new_title: str) -> bool:
    """Renames a session (works for both RAM and DB sessions)."""
    if session_id in _ram_sessions:
        _ram_sessions[session_id]["title"] = new_title
        return True
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = sqlite3.connect(PATH_DB)
        cur  = conn.cursor()
        cur.execute("UPDATE sessions SET title = ?, updated_at = ? WHERE id = ?", (new_title, now, session_id))
        conn.commit()
        conn.close()
        logger.info(f"[SESSION] Renamed {session_id} to '{new_title}'")
        return True
    except Exception as e:
        logger.error(f"[SESSION] rename_session error: {e}")
        return False


def change_session_mode(session_id: str, new_mode: str) -> bool:
    """Changes the privacy mode of a session, moving it between DB and RAM if necessary."""
    old_sess = get_session(session_id)
    if not old_sess:
        return False
        
    old_mode = old_sess["privacy_mode"]
    if old_mode == new_mode:
        return True
        
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
    # DB -> RAM
    if not _is_ram_mode(old_mode) and _is_ram_mode(new_mode):
        messages = get_session_messages(session_id)
        
        _ram_sessions[session_id] = {
            "id": session_id,
            "title": old_sess["title"],
            "created_at": old_sess["created_at"],
            "updated_at": now,
            "privacy_mode": new_mode,
            "is_incognito": 1 if new_mode == "incognito" else 0,
            "messages": messages
        }
        
        try:
            conn = sqlite3.connect(PATH_DB)
            cur = conn.cursor()
            cur.execute("DELETE FROM history WHERE session_id = ?", (session_id,))
            cur.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            conn.commit()
            conn.close()
            logger.info(f"[SESSION] Moved DB session {session_id} to RAM -> {new_mode}")
        except Exception as e:
            logger.error(f"[SESSION] DB->RAM move error: {e}")
            
    # RAM -> DB
    elif _is_ram_mode(old_mode) and not _is_ram_mode(new_mode):
        sess = _ram_sessions[session_id]
        try:
            conn = sqlite3.connect(PATH_DB)
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO sessions (id, title, created_at, updated_at, privacy_mode, is_incognito) VALUES (?, ?, ?, ?, ?, ?)",
                (session_id, sess["title"], sess["created_at"], now, new_mode, 0)
            )
            for m in sess["messages"]:
                cur.execute(
                    "INSERT INTO history (timestamp, role, message, session_id) VALUES (?, ?, ?, ?)",
                    (m["timestamp"], m["role"], m["message"], session_id)
                )
            conn.commit()
            conn.close()
            logger.info(f"[SESSION] Moved RAM session {session_id} to DB -> {new_mode}")
        except Exception as e:
            logger.error(f"[SESSION] RAM->DB move error: {e}")
            
        del _ram_sessions[session_id]
        
    else:
        # Same storage tier
        if session_id in _ram_sessions:
            _ram_sessions[session_id]["privacy_mode"] = new_mode
            _ram_sessions[session_id]["is_incognito"] = 1 if new_mode == "incognito" else 0
        else:
            try:
                conn = sqlite3.connect(PATH_DB)
                cur = conn.cursor()
                cur.execute("UPDATE sessions SET privacy_mode = ?, is_incognito = ?, updated_at = ? WHERE id = ?", 
                            (new_mode, 1 if new_mode == "incognito" else 0, now, session_id))
                conn.commit()
                conn.close()
            except Exception as e:
                logger.error(f"[SESSION] Mode update error: {e}")

    return True


def touch_session(session_id: str):
    """Updates the updated_at timestamp."""
    if session_id in _ram_sessions:
        _ram_sessions[session_id]["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = sqlite3.connect(PATH_DB)
        cur  = conn.cursor()
        cur.execute("UPDATE sessions SET updated_at = ? WHERE id = ?", (now, session_id))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning(f"[SESSION] touch_session error: {e}")


def delete_session(session_id: str) -> bool:
    """Deletes a session from RAM or DB."""
    if session_id in _ram_sessions:
        del _ram_sessions[session_id]
        logger.info(f"[SESSION] Deleted RAM session {session_id}")
        return True
    try:
        conn = sqlite3.connect(PATH_DB)
        cur  = conn.cursor()
        cur.execute("DELETE FROM history WHERE session_id = ?", (session_id,))
        cur.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        conn.commit()
        conn.close()
        _purge_vault_sessions([session_id])
        conn2 = sqlite3.connect(PATH_DB)
        conn2.execute("VACUUM")
        conn2.close()
        logger.info(f"[SESSION] Deleted DB session {session_id}")
        return True
    except Exception as e:
        logger.error(f"[SESSION] delete_session error: {e}")
        return False
