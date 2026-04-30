"""
MODULE: Brain Interface - Hecos Memory Vault
DESCRIPTION: Centralized manager for semantic and episodic memory.
             Supports per-user memory scoping via user_id parameter.
             Respects the 'cognition' config section for all operations.
"""

import json
import os
import sqlite3
from datetime import datetime
from hecos.core.logging import logger

# Base memory directory
ROOT_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
BASE_DIR  = os.path.join(ROOT_DIR, "memory")

# Legacy single-user paths (kept for backward compat / migration)
PATH_IDENTITY = os.path.join(BASE_DIR, "core_identity.json")

# Per-user vault paths
_USERS_DIR = os.path.join(BASE_DIR, "users")

# Cache to prevent duplicate logs during repeated saves
_initialized_vaults = set()


# ── Vault path helpers ─────────────────────────────────────────────────────────

def _vault(user_id: str = "admin") -> str:
    """Returns the path to the user's vault directory, creating it if needed."""
    path = os.path.join(_USERS_DIR, user_id)
    os.makedirs(path, exist_ok=True)
    return path

def _profile_path(user_id: str = "admin") -> str:
    return os.path.join(_vault(user_id), "profile.json")

def _db_path(user_id: str = "admin") -> str:
    return os.path.join(_vault(user_id), "history.db")

def _avatar_path(user_id: str = "admin") -> str:
    return os.path.join(_vault(user_id), "avatar.jpg")


# ── Config helpers ─────────────────────────────────────────────────────────────

def _get_cognition(config) -> dict:
    """Returns the cognition sub-section from a config dict or ConfigManager."""
    if config is None:
        return {}
    if hasattr(config, "config") and isinstance(config.config, dict):
        cfg_dict = config.config
    elif isinstance(config, dict):
        cfg_dict = config
    else:
        return {}
    return cfg_dict.get("cognition", {})


def is_memory_enabled(config: dict = None) -> bool:
    """True if both memory_enabled and episodic_memory are ON."""
    cog = _get_cognition(config)
    return cog.get("memory_enabled", True) and cog.get("episodic_memory", True)


def get_max_history(config: dict = None) -> int:
    """Returns the max number of history messages to include in context."""
    cog = _get_cognition(config)
    return int(cog.get("max_history_messages", 15))


# ── Vault management ───────────────────────────────────────────────────────────

def initialize_vault():
    """Creates the legacy base folder (for backward compat). Prefer initialize_user_vault."""
    os.makedirs(BASE_DIR, exist_ok=True)
    logger.info(f"[MEMORY] Legacy vault checked at: {BASE_DIR}")
    
    # Run session manager migration to ensure `sessions` table is created
    try:
        from hecos.memory import session_manager
        session_manager.migrate_schema()
    except Exception as e:
        logger.error(f"[MEMORY] Failed to migrate session schema: {e}")


def initialize_user_vault(user_id: str = "admin"):
    """Creates vault directory and DB schema for the given user."""
    db = _db_path(user_id)
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            role TEXT,
            message TEXT
        )
    ''')
    conn.commit()
    conn.close()
    
    if user_id not in _initialized_vaults:
        logger.info(f"[MEMORY] Vault initialized for user '{user_id}' at: {db}")
        _initialized_vaults.add(user_id)


def maybe_clear_on_restart(config: dict, user_id: str = "admin"):
    """Clears the episodic history if clear_on_restart is enabled in config."""
    cog = _get_cognition(config)
    if cog.get("clear_on_restart", False):
        cleared = clear_history(user_id=user_id)
        if cleared:
            logger.info(f"[MEMORY] History cleared on restart for '{user_id}'.")


# ── Context retrieval ──────────────────────────────────────────────────────────

def get_context(config: dict = None, dynamic_name: str = None,
                user_id: str = "admin") -> str:
    """Retrieves AI and user identity for the System Prompt."""
    cog = _get_cognition(config)
    if not cog.get("include_identity_context", True):
        return ""
    try:
        # Load core AI identity (shared)
        id_data = {}
        if os.path.exists(PATH_IDENTITY):
            with open(PATH_IDENTITY, "r", encoding="utf-8") as f:
                id_data = json.load(f)

        # Load per-user profile notes
        prof_path = _profile_path(user_id)
        prof_data = {}
        if os.path.exists(prof_path):
            with open(prof_path, "r", encoding="utf-8") as f:
                prof_data = json.load(f)

        from hecos.core.system.version import VERSION
        context = "\n[ACTIVE IDENTITY MEMORY]\n"

        fallback_name = id_data.get('ai', {}).get('name', 'Hecos')
        ai_name = dynamic_name or fallback_name

        if dynamic_name and dynamic_name.lower() != "hecos":
            context += f"You are {ai_name}, running on core version {VERSION}.\n"
            user_label = prof_data.get("display_name") or id_data.get('author', {}).get('name', user_id)
            context += f"Your user/interlocutor is {user_label}.\n"
        else:
            ai_nature   = id_data.get('ai', {}).get('nature', 'AI Assistant')
            ai_protocol = id_data.get('ai', {}).get('protocol', 'Standard')
            context += f"You are {ai_name}, version {VERSION}. {ai_nature}.\n"
            user_label = prof_data.get("display_name") or id_data.get('author', {}).get('name', user_id)
            context += f"Your Creator (Admin) is {user_label}. Protocol: {ai_protocol}.\n"

        # User notes from profile
        notes = prof_data.get('notes') or id_data.get('author', {}).get('notes', '')
        if notes:
            context += f"User notes: {notes}\n"

        # Avatar context hint (for Vision models)
        av = _avatar_path(user_id)
        if os.path.exists(av):
            context += f"[USER_AVATAR_PATH: {av}]\n"

        return context
    except Exception as e:
        logger.error(f"Memory Context Error: {e}")
        return ""


def update_profile(key, value, user_id: str = "admin"):
    """Updates a specific field in the user's profile JSON."""
    try:
        prof_path = _profile_path(user_id)
        if not os.path.exists(prof_path):
            data = {"display_name": user_id, "notes": ""}
        else:
            with open(prof_path, "r", encoding="utf-8") as f:
                data = json.load(f)

        data[key] = value

        with open(prof_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        return True
    except Exception as e:
        logger.error(f"Profile Update Error: {e}")
        return False


# ── Episodic memory (chat history) ────────────────────────────────────────────

def save_message(role, message, config: dict = None, user_id: str = "admin", session_id: str = None):
    """Stores an exchange in episodic memory, respecting config flags and privacy mode.
    - incognito → discard entirely (no storage anywhere)
    - auto_wipe → store in RAM only (vanishes on restart)
    - normal    → persist in SQLite DB as usual
    """
    if not is_memory_enabled(config):
        return

    try:
        from hecos.core.privacy import privacy_manager
        if not session_id:
            session_id = privacy_manager.get_session_id()

        if privacy_manager.is_incognito():
            # Total privacy: discard message, write nothing
            return

        if privacy_manager.is_auto_wipe():
            # RAM-only: store in session_manager's in-memory store
            from hecos.memory import session_manager
            if session_id:
                session_manager.add_ram_message(session_id, role, message)
            return

    except Exception:
        pass

    try:
        from hecos.memory import session_manager

        initialize_user_vault(user_id)

        with sqlite3.connect(session_manager.PATH_DB, timeout=20) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO history (timestamp, role, message, session_id) VALUES (?, ?, ?, ?)",
                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), role, message, session_id)
            )
            conn.commit()

        if session_id:
            try:
                session_manager.touch_session(session_id)
            except Exception:
                pass

    except Exception as e:
        logger.error(f"[MEMORY] Save Error: {e}")


def get_history(limit: int = None, config: dict = None, user_id: str = "admin", session_id: str = None) -> list:
    """Retrieves the last N messages from history, filtered by session if provided.
    For RAM sessions (auto_wipe/incognito), reads from the in-memory store.
    """
    if limit is None:
        limit = get_max_history(config)
    try:
        from hecos.memory import session_manager

        if not session_id:
            try:
                from hecos.core.privacy import privacy_manager
                session_id = privacy_manager.get_session_id()
            except:
                pass

        # ── RAM session (auto_wipe / incognito) ───────────────────────────────
        if session_id and session_id in session_manager._ram_sessions:
            messages = session_manager.get_session_messages(session_id)
            pairs = [(m['role'], m['message']) for m in messages]
            return pairs[-limit:] if limit else pairs

        # ── Normal DB session ─────────────────────────────────────────────────
        if not os.path.exists(session_manager.PATH_DB):
            return []

        with sqlite3.connect(session_manager.PATH_DB, timeout=20) as conn:
            cursor = conn.cursor()
            if session_id:
                cursor.execute(
                    "SELECT role, message FROM history WHERE session_id = ? ORDER BY id DESC LIMIT ?",
                    (session_id, limit)
                )
            else:
                cursor.execute(
                    "SELECT role, message FROM history ORDER BY id DESC LIMIT ?",
                    (limit,)
                )
            rows = cursor.fetchall()

        rows.reverse()
        return rows
    except Exception as e:
        logger.error(f"[MEMORY] Read Error: {e}")
        return []


def clear_history(days: int = None, user_id: str = "admin") -> bool:
    """
    Wipes the episodic history from the user's DB.
    If days is specified, only deletes messages older than now - days.
    """
    try:
        db = _db_path(user_id)
        if not os.path.exists(db):
            return True
        conn = sqlite3.connect(db)
        cursor = conn.cursor()

        if days is None:
            cursor.execute("DELETE FROM history")
            msg = f"[MEMORY] All history cleared for '{user_id}'."
        else:
            from datetime import timedelta
            cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("DELETE FROM history WHERE timestamp < ?", (cutoff,))
            msg = f"[MEMORY] History older than {days} days cleared for '{user_id}'."

        conn.commit()
        cursor.execute("VACUUM")
        conn.close()
        logger.info(f"{msg} Database vacuumed.")
        return True
    except Exception as e:
        logger.error(f"Memory Reset Error: {e}")
        return False


def get_memory_stats(user_id: str = "admin") -> dict:
    """Returns basic metrics for a user's memory vault."""
    try:
        db = _db_path(user_id)
        count = 0
        if os.path.exists(db):
            conn = sqlite3.connect(db)
            count = conn.execute("SELECT COUNT(*) FROM history").fetchone()[0]
            conn.close()
        return {"total_messages": count, "db_path": db}
    except Exception as e:
        logger.error(f"Memory Stats Error: {e}")
        return {"total_messages": 0, "error": str(e)}


# ── Aliases ────────────────────────────────────────────────────────────────────

def get_memory_context(config: dict = None, user_id: str = "admin") -> str:
    """Alias for get_context()."""
    return get_context(config, user_id=user_id)