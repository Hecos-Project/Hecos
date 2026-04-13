"""
MODULE: Chat Session Manager
DESCRIPTION: Manages named chat sessions in the episodic memory vault.
             Provides create/read/update/delete operations for sessions,
             and handles the non-destructive migration of the legacy flat history.
"""

import os
import sqlite3
import uuid
from datetime import datetime
from zentra.core.logging import logger

# Re-use the same DB path as memory/__init__.py
ROOT_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
BASE_DIR  = os.path.join(ROOT_DIR, "memory")
PATH_DB   = os.path.join(BASE_DIR, "chat_history.db")


# ──────────────────────────────────────────────────────────────────────────────
# SCHEMA MIGRATION
# ──────────────────────────────────────────────────────────────────────────────

def migrate_schema():
    """
    Non-destructive migration.
    - Creates the `sessions` table if missing.
    - Adds `session_id` and `session_title` columns to `history` if missing.
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
            is_incognito INTEGER DEFAULT 0
        )
    """)

    # 2. Add session_id to history (if not already there)
    existing_cols = [row[1] for row in cur.execute("PRAGMA table_info(history)").fetchall()]
    if "session_id" not in existing_cols:
        cur.execute("ALTER TABLE history ADD COLUMN session_id TEXT")
        logger.info("[SESSION] Added session_id column to history table.")

    # 3. Migrate legacy messages (session_id IS NULL) to a 'Legacy' session
    cur.execute("SELECT COUNT(*) FROM history WHERE session_id IS NULL")
    legacy_count = cur.fetchone()[0]

    if legacy_count > 0:
        legacy_id = "legacy-" + datetime.now().strftime("%Y%m%d")
        # Ensure legacy session exists
        cur.execute("SELECT id FROM sessions WHERE id = ?", (legacy_id,))
        if not cur.fetchone():
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cur.execute(
                "INSERT INTO sessions (id, title, created_at, updated_at, privacy_mode) VALUES (?, ?, ?, ?, ?)",
                (legacy_id, "Legacy Conversations", now, now, "normal")
            )
        cur.execute("UPDATE history SET session_id = ? WHERE session_id IS NULL", (legacy_id,))
        logger.info(f"[SESSION] Migrated {legacy_count} legacy messages to session '{legacy_id}'.")

    conn.commit()
    conn.close()
    logger.info("[SESSION] Schema migration complete.")


# ──────────────────────────────────────────────────────────────────────────────
# SESSION CRUD
# ──────────────────────────────────────────────────────────────────────────────

def create_session(title: str = None, privacy_mode: str = "normal") -> str:
    """Creates a new chat session and returns its ID."""
    session_id = str(uuid.uuid4())
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if not title:
        title = f"Chat {datetime.now().strftime('%d/%m/%Y %H:%M')}"

    is_incognito = 1 if privacy_mode == "incognito" else 0

    conn = sqlite3.connect(PATH_DB)
    cur  = conn.cursor()
    cur.execute(
        "INSERT INTO sessions (id, title, created_at, updated_at, privacy_mode, is_incognito) VALUES (?, ?, ?, ?, ?, ?)",
        (session_id, title, now, now, privacy_mode, is_incognito)
    )
    conn.commit()
    conn.close()
    logger.info(f"[SESSION] Created session: {session_id} '{title}' (mode={privacy_mode})")
    return session_id


def get_sessions() -> list:
    """Returns all sessions ordered by most recent first, with message count."""
    try:
        conn = sqlite3.connect(PATH_DB)
        conn.row_factory = sqlite3.Row
        cur  = conn.cursor()
        cur.execute("""
            SELECT s.id, s.title, s.created_at, s.updated_at, s.privacy_mode, s.is_incognito,
                   COUNT(h.id) as message_count
            FROM sessions s
            LEFT JOIN history h ON h.session_id = s.id
            GROUP BY s.id
            ORDER BY s.updated_at DESC
        """)
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows
    except Exception as e:
        logger.error(f"[SESSION] get_sessions error: {e}")
        return []


def get_session(session_id: str) -> dict | None:
    """Returns metadata for a single session."""
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
    """Returns all messages belonging to a session in chronological order."""
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


def rename_session(session_id: str, new_title: str) -> bool:
    """Renames a session."""
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


def touch_session(session_id: str):
    """Updates the updated_at timestamp of a session (called when a message is added)."""
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
    """Deletes a session and all its messages."""
    try:
        conn = sqlite3.connect(PATH_DB)
        cur  = conn.cursor()
        cur.execute("DELETE FROM history WHERE session_id = ?", (session_id,))
        cur.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        conn.commit()
        conn.close()
        # VACUUM must run outside any transaction
        conn2 = sqlite3.connect(PATH_DB)
        conn2.execute("VACUUM")
        conn2.close()
        logger.info(f"[SESSION] Deleted session {session_id} and all its messages.")
        return True
    except Exception as e:
        logger.error(f"[SESSION] delete_session error: {e}")
        return False


def wipe_session_messages(session_id: str) -> bool:
    """Deletes only the messages of a session (for auto-wipe mode). Keeps the entry."""
    try:
        conn = sqlite3.connect(PATH_DB)
        cur  = conn.cursor()
        cur.execute("DELETE FROM history WHERE session_id = ?", (session_id,))
        conn.commit()
        conn.close()
        logger.info(f"[SESSION] Wiped messages for session {session_id}.")
        return True
    except Exception as e:
        logger.error(f"[SESSION] wipe_session_messages error: {e}")
        return False
