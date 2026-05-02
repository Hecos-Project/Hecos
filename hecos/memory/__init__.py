"""
MODULE: Brain Interface - Hecos Memory Vault
DESCRIPTION: Centralized manager for semantic and episodic memory.
             Respects the 'cognition' config section for all operations.
"""

import json
import os
import sqlite3
from datetime import datetime
from hecos.core.logging import logger

# File paths (forced absolute to avoid working-directory confusion)
ROOT_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
BASE_DIR = os.path.join(ROOT_DIR, "memory")
PATH_IDENTITY = os.path.join(BASE_DIR, "core_identity.json")
PATH_PROFILE   = os.path.join(BASE_DIR, "user_profile.json")
PATH_DB        = os.path.join(BASE_DIR, "chat_history.db")

# â”€â”€ Config helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _get_cognition(config) -> dict:
    """Returns the cognition sub-section from a config dict or ConfigManager."""
    if config is None:
        return {}
    
    # Extract raw dictionary if it's a ConfigManager
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


# â”€â”€ Vault management â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def initialize_vault():
    """Creates the folder and databases if they don't exist, then runs schema migrations."""
    if not os.path.exists(BASE_DIR):
        os.makedirs(BASE_DIR)
    
    conn = sqlite3.connect(PATH_DB)
    cursor = conn.cursor()
    # Ensure the history table exists
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
    logger.info(f"[MEMORY] Vault initialized at: {os.path.abspath(PATH_DB)}")

    # Run session manager migration (non-destructive)
    try:
        from hecos.memory.session_manager import migrate_schema
        migrate_schema()
    except Exception as e:
        logger.warning(f"[MEMORY] Session schema migration skipped: {e}")


def maybe_clear_on_restart(config: dict):
    """Clears the episodic history if clear_on_restart is enabled in config."""
    cog = _get_cognition(config)
    if cog.get("clear_on_restart", False):
        cleared = clear_history()
        if cleared:
            logger.info("[MEMORY] History cleared on restart (clear_on_restart=True).")


# â”€â”€ Context retrieval â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def get_context(config: dict = None, dynamic_name: str = None) -> str:
    """Retrieves AI and Admin identity for the System Prompt."""
    cog = _get_cognition(config)
    if not cog.get("include_identity_context", True):
        return ""
    try:
        if not os.path.exists(PATH_IDENTITY) or not os.path.exists(PATH_PROFILE):
            return ""

        with open(PATH_IDENTITY, "r", encoding="utf-8") as f:
            id_data = json.load(f)
        
        with open(PATH_PROFILE, "r", encoding="utf-8") as f:
            prof_data = json.load(f)
            
        from hecos.core.system.version import VERSION
        context = f"\n[ACTIVE IDENTITY MEMORY]\n"
        
        # AI Identity
        fallback_name = id_data.get('ai', {}).get('name', 'Hecos')
        ai_name = dynamic_name or fallback_name
        
        if dynamic_name and dynamic_name.lower() != "hecos":
            # Neutral context for custom roleplays (Urania, MacGyver, etc.)
            context += f"You are {ai_name}, running on core version {VERSION}.\n"
            context += f"Your user/interlocutor is {id_data.get('author', {}).get('name', 'Admin')}.\n"
        else:
            # Full Hecos context
            ai_nature   = id_data.get('ai', {}).get('nature', 'AI Assistant')
            ai_protocol = id_data.get('ai', {}).get('protocol', 'Standard')
            context += f"You are {ai_name}, version {VERSION}. {ai_nature}.\n"
            context += f"Your Creator (Admin) is {id_data.get('author', {}).get('name', 'Admin')}. Protocol: {ai_protocol}.\n"
        
        # Admin Biographical Notes
        notes = prof_data.get('author', {}).get('notes', 'No specific notes.')
        context += f"Admin notes: {notes}\n"
        
        return context
    except Exception as e:
        logger.error(f"Memory Context Error: {e}")
        return ""


def update_profile(key, value):
    """Updates a specific field in the user profile JSON."""
    try:
        if not os.path.exists(PATH_PROFILE):
            # Create a default profile if missing
            data = {"author": {"name": "Admin", "role": "Root User", "notes": ""}}
        else:
            with open(PATH_PROFILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        
        # Ensure 'author' section exists
        if "author" not in data:
            data["author"] = {}
            
        # Standardize: we usually update 'notes'
        if key == "notes":
            data["author"]["notes"] = value
        else:
            data["author"][key] = value
            
        with open(PATH_PROFILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        return True
    except Exception as e:
        logger.error(f"Profile Update Error: {e}")
        return False


# â”€â”€ Episodic memory (chat history) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def save_message(role, message, config: dict = None, session_id: str = None):
    """Stores an exchange in episodic memory (DB), respecting config flags and privacy mode."""
    # Respect incognito mode — write nothing
    try:
        from hecos.core.privacy import privacy_manager
        if privacy_manager.is_incognito():
            return
        # Pick up session_id from privacy manager if not explicitly passed
        if session_id is None:
            session_id = privacy_manager.get_session_id()
    except Exception:
        pass

    if not is_memory_enabled(config):
        return
    try:
        with sqlite3.connect(PATH_DB, timeout=20) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO history (timestamp, role, message, session_id) VALUES (?, ?, ?, ?)",
                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), role, message, session_id)
            )
            conn.commit()
        # Update session timestamp
        if session_id:
            try:
                from hecos.memory.session_manager import touch_session
                touch_session(session_id)
            except Exception:
                pass
    except Exception as e:
        logger.error(f"Memory Save Error: {e}")


def get_history(limit: int = None, config: dict = None) -> list:
    """Retrieves the last N messages from the history."""
    if limit is None:
        limit = get_max_history(config)
    try:
        with sqlite3.connect(PATH_DB, timeout=20) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT role, message FROM history ORDER BY id DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            
        # Return in chronological order (oldest first)
        rows.reverse()
        return rows
    except Exception as e:
        logger.error(f"Memory Read Error: {e}")
        return []


def clear_history(days: int = None) -> bool:
    """
    Wipes the episodic history from the DB.
    If days is specified, only deletes messages older than now - days.
    """
    try:
        conn = sqlite3.connect(PATH_DB)
        cursor = conn.cursor()
        
        if days is None:
            cursor.execute("DELETE FROM history")
            msg = "[MEMORY] All history cleared."
        else:
            # Timestamp format is %Y-%m-%d %H:%M:%S
            from datetime import timedelta
            cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("DELETE FROM history WHERE timestamp < ?", (cutoff,))
            msg = f"[MEMORY] History older than {days} days cleared."
        
        conn.commit()
        # Shrink the file size on disk
        cursor.execute("VACUUM")
        conn.close()
        logger.info(f"{msg} Database vacuumed.")
        return True
    except Exception as e:
        logger.error(f"Memory Reset Error: {e}")
        return False


# â”€â”€ Aliases â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def get_memory_context(config: dict = None) -> str:
    """Alias for get_context()."""
    return get_context(config)