"""
MODULE: Chat Session Manager
DESCRIPTION: Manages named chat sessions.
             - 'normal' sessions: persisted in SQLite DB across restarts.
             - 'auto_wipe' sessions: RAM-only (visible while app runs, vanish on restart).
               Messages are kept in memory and available when switching back to the session.
             - 'incognito' sessions: RAM-only, zero writes to disk.
             Both non-normal modes never touch the DB.
"""

import os
import sqlite3
import uuid
from datetime import datetime
from hecos.core.logging import logger

# Re-use the same DB path as memory/__init__.py
ROOT_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
BASE_DIR  = os.path.join(ROOT_DIR, "memory")
PATH_DB   = os.path.join(BASE_DIR, "chat_history.db")

# ──────────────────────────────────────────────────────────────────────────────
# IN-MEMORY STORE  (auto_wipe + incognito sessions — vanish on restart)
# Structure:
#   _ram_sessions = { session_id: { id, title, created_at, updated_at,
#                                   privacy_mode, is_incognito,
#                                   messages: [ {id, timestamp, role, message} ] } }
# ──────────────────────────────────────────────────────────────────────────────

_ram_sessions: dict = {}


def _is_ram_mode(privacy_mode: str) -> bool:
    """Returns True for modes that must never touch the DB."""
    return privacy_mode in ("auto_wipe", "incognito")


# ──────────────────────────────────────────────────────────────────────────────
# SCHEMA MIGRATION
# ──────────────────────────────────────────────────────────────────────────────

def migrate_schema():
    """
    Non-destructive migration.
    - Creates the `sessions` table if missing.
    - Adds `session_id` column to `history` if missing.
    - Assigns all legacy (untagged) messages to a 'Legacy' session.
    """
    conn = sqlite3.connect(PATH_DB)
    cur  = conn.cursor()

    # 1. Create sessions table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id          TEXT PRIMARY KEY,
            title       TEXT NOT NULL,
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL,
            privacy_mode TEXT DEFAULT 'normal',
            is_incognito INTEGER DEFAULT 0,
            is_archived  INTEGER DEFAULT 0
        )
    """)

    # 2. Add session_id to history (if not already there)
    hist_cols = [row[1] for row in cur.execute("PRAGMA table_info(history)").fetchall()]
    if "session_id" not in hist_cols:
        cur.execute("ALTER TABLE history ADD COLUMN session_id TEXT")
        logger.info("[SESSION] Added session_id column to history table.")
        
    sess_cols = [row[1] for row in cur.execute("PRAGMA table_info(sessions)").fetchall()]
    if "is_archived" not in sess_cols:
        cur.execute("ALTER TABLE sessions ADD COLUMN is_archived INTEGER DEFAULT 0")
        logger.info("[SESSION] Added is_archived column to sessions table.")

    # 3. Clean up any legacy auto_wipe/incognito sessions that were wrongly saved to DB in the past
    cur.execute("DELETE FROM history WHERE session_id IN (SELECT id FROM sessions WHERE privacy_mode IN ('auto_wipe', 'incognito'))")
    cur.execute("DELETE FROM sessions WHERE privacy_mode IN ('auto_wipe', 'incognito')")

    # 4. Migrate legacy messages (session_id IS NULL) to a 'Legacy' session
    cur.execute("SELECT COUNT(*) FROM history WHERE session_id IS NULL")
    legacy_count = cur.fetchone()[0]

    if legacy_count > 0:
        legacy_id = "legacy-" + datetime.now().strftime("%Y%m%d")
        cur.execute("SELECT id FROM sessions WHERE id = ?", (legacy_id,))
        if not cur.fetchone():
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            legacy_title = "Chat " + datetime.now().strftime("%d/%m/%Y")
            cur.execute(
                "INSERT INTO sessions (id, title, created_at, updated_at, privacy_mode) VALUES (?, ?, ?, ?, ?)",
                (legacy_id, legacy_title, now, now, "normal")
            )
        cur.execute("UPDATE history SET session_id = ? WHERE session_id IS NULL", (legacy_id,))
        logger.info(f"[SESSION] Migrated {legacy_count} legacy messages to session '{legacy_id}'.")

    # 5. One-time rename of any sessions still carrying the old "Legacy Conversations" label
    cur.execute("SELECT id, created_at FROM sessions WHERE title = 'Legacy Conversations'")
    old_legacy_rows = cur.fetchall()
    for row_id, row_created in old_legacy_rows:
        try:
            # Use the session's own created_at date for the new title
            dt = datetime.strptime(row_created[:10], "%Y-%m-%d")
            new_title = "Chat " + dt.strftime("%d/%m/%Y")
        except Exception:
            new_title = "Chat (storica)"
        cur.execute("UPDATE sessions SET title = ? WHERE id = ?", (new_title, row_id))
    if old_legacy_rows:
        logger.info(f"[SESSION] Renamed {len(old_legacy_rows)} legacy session(s) to date-based titles.")

    conn.commit()
    conn.close()
    logger.info("[SESSION] Schema migration complete.")


# ──────────────────────────────────────────────────────────────────────────────
# SESSION CRUD  (DB for normal, RAM for auto_wipe/incognito)
# ──────────────────────────────────────────────────────────────────────────────

def create_session(title: str = None, privacy_mode: str = "normal") -> str:
    """Creates a new chat session. Normal → DB. auto_wipe/incognito → RAM only."""
    session_id = str(uuid.uuid4())
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if not title:
        title = f"Chat {datetime.now().strftime('%d/%m/%Y %H:%M')}"

    if _is_ram_mode(privacy_mode):
        # ── RAM-only session ──────────────────────────────────────────────────
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
        # ── DB-persisted session ──────────────────────────────────────────────
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

    # ── DB sessions (normal) ──────────────────────────────────────────────────
    try:
        conn = sqlite3.connect(PATH_DB)
        conn.row_factory = sqlite3.Row
        cur  = conn.cursor()
        
        query = """
            SELECT s.id, s.title, s.created_at, s.updated_at, s.privacy_mode, s.is_incognito, s.is_archived,
                   COUNT(h.id) as message_count
            FROM sessions s
            LEFT JOIN history h ON h.session_id = s.id
            WHERE s.privacy_mode = 'normal'
        """
        if not include_archived:
            query += " AND s.is_archived = 0 "
        else:
            query += " AND s.is_archived = 1 "
            
        query += """
            GROUP BY s.id
            ORDER BY s.updated_at DESC
        """
        cur.execute(query)
        results = [dict(r) for r in cur.fetchall()]
        conn.close()
    except Exception as e:
        logger.error(f"[SESSION] get_sessions DB error: {e}")

    # ── RAM sessions (auto_wipe + incognito) ──────────────────────────────────
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

    # Merge: RAM sessions interleaved by updated_at, most recent first
    all_sessions = ram_rows + results
    all_sessions.sort(key=lambda s: s.get("updated_at", ""), reverse=True)
    return all_sessions


def get_session(session_id: str) -> dict | None:
    """Returns metadata for a single session (checks RAM first, then DB)."""
    # Check RAM first
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
    # Fall back to DB
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
    # Check RAM first
    if session_id in _ram_sessions:
        return list(_ram_sessions[session_id]["messages"])
    # Fall back to DB
    try:
        conn = sqlite3.connect(PATH_DB)
        cur  = conn.cursor()
        cur.execute(
            "SELECT id, timestamp, role, message FROM history WHERE session_id = ? ORDER BY id ASC",
            (session_id,)
        )
        rows = cur.fetchall()
        conn.close()
        return [{"id": r[0], "timestamp": r[1], "role": r[2], "message": r[3]} for r in rows]
    except Exception as e:
        logger.error(f"[SESSION] get_session_messages error: {e}")
        return []


def add_ram_message(session_id: str, role: str, message: str):
    """
    Appends a message to a RAM session's in-memory store.
    Called by brain_interface instead of the DB write path when the mode is non-normal.
    """
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
        # RAM sessions don't support persistence/archiving; "closing" them implies deletion.
        # But we return True to avoid API errors if the UI calls it.
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
        
    # Moving from DB to RAM
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
            
    # Moving from RAM to DB
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
        # Same storage tier (e.g. auto_wipe -> incognito)
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
    """Updates the updated_at timestamp (used when a message is added to a DB session)."""
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
    """Deletes a session. RAM sessions are removed from memory; DB sessions from SQLite."""
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
        # optimize space
        conn2 = sqlite3.connect(PATH_DB)
        conn2.execute("VACUUM")
        conn2.close()
        logger.info(f"[SESSION] Deleted DB session {session_id}")
        return True
    except Exception as e:
        logger.error(f"[SESSION] delete_session error: {e}")
        return False


def delete_all_sessions() -> bool:
    """Deletes all sessions across RAM and DB. Returns True if successful."""
    _ram_sessions.clear()
    try:
        conn = sqlite3.connect(PATH_DB)
        cur  = conn.cursor()
        cur.execute("DELETE FROM history")
        cur.execute("DELETE FROM sessions")
        conn.commit()
        conn.close()
        
        conn2 = sqlite3.connect(PATH_DB)
        conn2.execute("VACUUM")
        conn2.close()
        logger.info("[SESSION] Deleted all sessions (RAM & DB)")
        return True
    except Exception as e:
        logger.error(f"[SESSION] delete_all_sessions error: {e}")
        return False


def wipe_session_messages(session_id: str) -> bool:
    """
    Wipes messages from a session.
    For RAM sessions: clears the messages list (keeps the session entry).
    For DB sessions: deletes history rows (legacy auto-wipe path, kept for compatibility).
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
