"""
hecos/memory/session_db.py
Database utilities and schema migration for sessions.
"""
import os
import sqlite3
from datetime import datetime
import glob
from hecos.core.logging import logger
from hecos.memory.session_state import BASE_DIR, PATH_DB

def _purge_vault_sessions(session_ids: list):
    """
    Deletes all history rows for the given session_ids from every user vault DB.
    This prevents orphaned messages after a session-table wipe.
    """
    if not session_ids:
        return
    try:
        users_dir = os.path.join(BASE_DIR, "users")
        if not os.path.exists(users_dir):
            return
        pattern = os.path.join(users_dir, "*", "history.db")
        vault_dbs = glob.glob(pattern)
        holders = ",".join("?" for _ in session_ids)
        for db_path in vault_dbs:
            try:
                with sqlite3.connect(db_path, timeout=10) as conn:
                    conn.execute(f"DELETE FROM history WHERE session_id IN ({holders})", session_ids)
                    conn.commit()
            except Exception as e:
                logger.warning(f"[SESSION] _purge_vault_sessions error for {db_path}: {e}")
    except Exception as e:
        logger.warning(f"[SESSION] _purge_vault_sessions outer error: {e}")


def migrate_schema():
    """
    Non-destructive migration.
    - Creates the `sessions` table if missing.
    - Adds `session_id` column to `history` if missing.
    - Assigns all legacy (untagged) messages to a 'Legacy' session.
    """
    conn = sqlite3.connect(PATH_DB)
    cur  = conn.cursor()

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

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='history'")
    has_history = cur.fetchone() is not None

    if has_history:
        hist_cols = [row[1] for row in cur.execute("PRAGMA table_info(history)").fetchall()]
        if "session_id" not in hist_cols:
            cur.execute("ALTER TABLE history ADD COLUMN session_id TEXT")
            logger.info("[SESSION] Added session_id column to history table.")
            
    sess_cols = [row[1] for row in cur.execute("PRAGMA table_info(sessions)").fetchall()]
    if "is_archived" not in sess_cols:
        cur.execute("ALTER TABLE sessions ADD COLUMN is_archived INTEGER DEFAULT 0")
        logger.info("[SESSION] Added is_archived column to sessions table.")

    if has_history:
        cur.execute("DELETE FROM history WHERE session_id IN (SELECT id FROM sessions WHERE privacy_mode IN ('auto_wipe', 'incognito'))")
    
    cur.execute("DELETE FROM sessions WHERE privacy_mode IN ('auto_wipe', 'incognito')")

    if has_history:
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

    cur.execute("SELECT id, created_at FROM sessions WHERE title = 'Legacy Conversations'")
    old_legacy_rows = cur.fetchall()
    for row_id, row_created in old_legacy_rows:
        try:
            dt = datetime.strptime(row_created[:10], "%Y-%m-%d")
            new_title = "Chat " + dt.strftime("%d/%m/%Y")
        except Exception:
            new_title = "Chat (storica)"
        cur.execute("UPDATE sessions SET title = ? WHERE id = ?", (new_title, row_id))
    if old_legacy_rows:
        logger.info(f"[SESSION] Renamed {len(old_legacy_rows)} legacy session(s) to date-based titles.")

    conn.commit()
    conn.close()
    
    # Run the new session config db init
    try:
        from hecos.memory.session_config_db import init_session_config_db
        init_session_config_db()
    except Exception as e:
        logger.warning(f"[SESSION] session_config_db init skipped: {e}")

    logger.info("[SESSION] Schema migration complete.")
