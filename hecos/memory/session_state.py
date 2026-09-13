"""
hecos/memory/session_state.py
Holds shared state and database paths for session management.
"""
import os

ROOT_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
BASE_DIR  = os.path.join(ROOT_DIR, "memory")
PATH_DB   = os.path.join(BASE_DIR, "chat_history.db")

# IN-MEMORY STORE (auto_wipe + incognito sessions — vanish on restart)
_ram_sessions: dict = {}

def _is_ram_mode(privacy_mode: str) -> bool:
    """Returns True for modes that must never touch the DB."""
    return privacy_mode in ("auto_wipe", "incognito")
