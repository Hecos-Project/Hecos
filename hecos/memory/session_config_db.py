"""
hecos/memory/session_config_db.py
Manages the per-session configuration overrides stored as JSON.
"""
import sqlite3
import json
from hecos.core.logging import logger
from hecos.memory.session_state import PATH_DB, _ram_sessions

def init_session_config_db():
    """Ensures the config_override column exists in the sessions table."""
    conn = sqlite3.connect(PATH_DB)
    cur = conn.cursor()
    try:
        cur.execute("PRAGMA table_info(sessions)")
        cols = [row[1] for row in cur.fetchall()]
        if "config_override" not in cols:
            cur.execute("ALTER TABLE sessions ADD COLUMN config_override TEXT")
            logger.info("[SESSION_CONFIG] Added config_override column to sessions table.")
            conn.commit()
    except Exception as e:
        logger.error(f"[SESSION_CONFIG] Failed to init DB: {e}")
    finally:
        conn.close()

def get_session_config(session_id: str) -> dict:
    """Retrieves the configuration override for a session."""
    if not session_id:
        return {}
    if session_id in _ram_sessions:
        return _ram_sessions[session_id].get("config_override", {})
        
    try:
        conn = sqlite3.connect(PATH_DB)
        cur = conn.cursor()
        cur.execute("SELECT config_override FROM sessions WHERE id = ?", (session_id,))
        row = cur.fetchone()
        conn.close()
        if row and row[0]:
            return json.loads(row[0])
    except Exception as e:
        logger.warning(f"[SESSION_CONFIG] Error getting config for {session_id}: {e}")
    return {}

def set_session_config(session_id: str, overrides: dict) -> bool:
    """Sets the configuration override for a session."""
    if not session_id:
        return False
    if session_id in _ram_sessions:
        _ram_sessions[session_id]["config_override"] = overrides
        return True
        
    try:
        conn = sqlite3.connect(PATH_DB)
        cur = conn.cursor()
        data = json.dumps(overrides) if overrides else None
        cur.execute("UPDATE sessions SET config_override = ? WHERE id = ?", (data, session_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.warning(f"[SESSION_CONFIG] Error setting config for {session_id}: {e}")
        return False
