"""
MODULE: Brain Interface - Zentra Memory Vault
DESCRIPTION: Centralized manager for semantic and episodic memory.
             Respects the 'cognition' config section for all operations.
"""

import json
import os
import sqlite3
from datetime import datetime
from core.logging import logger

# File paths
BASE_DIR = "memory"
PATH_IDENTITY = os.path.join(BASE_DIR, "core_identity.json")
PATH_PROFILE   = os.path.join(BASE_DIR, "user_profile.json")
PATH_DB        = os.path.join(BASE_DIR, "chat_history.db")

# ── Config helpers ─────────────────────────────────────────────────────────────

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
    return int(cog.get("max_history_messages", 20))


# ── Vault management ───────────────────────────────────────────────────────────

def initialize_vault():
    """Creates the folder and databases if they don't exist."""
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
    logger.info("[MEMORY] Vault initialized.")


def maybe_clear_on_restart(config: dict):
    """Clears the episodic history if clear_on_restart is enabled in config."""
    cog = _get_cognition(config)
    if cog.get("clear_on_restart", False):
        cleared = clear_history()
        if cleared:
            logger.info("[MEMORY] History cleared on restart (clear_on_restart=True).")


# ── Context retrieval ──────────────────────────────────────────────────────────

def get_context(config: dict = None) -> str:
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
            
        from core.system.version import VERSION
        context = f"\n[ACTIVE IDENTITY MEMORY]\n"
        
        # AI Identity
        ai_name     = id_data.get('ai', {}).get('name', 'Zentra')
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


# ── Episodic memory (chat history) ────────────────────────────────────────────

def save_message(role, message, config: dict = None):
    """Stores an exchange in episodic memory (DB), respecting config flags."""
    if not is_memory_enabled(config):
        return
    try:
        conn = sqlite3.connect(PATH_DB)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO history (timestamp, role, message) VALUES (?, ?, ?)",
                       (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), role, message))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Memory Save Error: {e}")


def get_history(limit: int = None, config: dict = None) -> list:
    """Retrieves the last N messages from the history."""
    if limit is None:
        limit = get_max_history(config)
    try:
        conn = sqlite3.connect(PATH_DB)
        cursor = conn.cursor()
        cursor.execute("SELECT role, message FROM history ORDER BY id DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        conn.close()
        
        # Return in chronological order (oldest first)
        rows.reverse()
        return rows
    except Exception as e:
        logger.error(f"Memory Read Error: {e}")
        return []


def clear_history() -> bool:
    """Wipes the episodic history table."""
    try:
        conn = sqlite3.connect(PATH_DB)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM history")
        conn.commit()
        conn.close()
        logger.info("[MEMORY] History cleared.")
        return True
    except Exception as e:
        logger.error(f"Memory Reset Error: {e}")
        return False


# ── Aliases ────────────────────────────────────────────────────────────────────

def get_memory_context(config: dict = None) -> str:
    """Alias for get_context()."""
    return get_context(config)