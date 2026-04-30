"""
MODULE: Privacy Manager
DESCRIPTION: Manages per-session privacy mode (normal, auto_wipe, incognito).
             Incognito = no writes to disk at all.
             Auto-wipe = data is written normally but deleted when the session is cleared.
"""

from hecos.core.logging import logger

# In-memory flag per current web session (does NOT persist across server restarts)
_current_mode: str = "normal"  # "normal" | "auto_wipe" | "incognito"
_current_session_id: str | None = None


def set_session(session_id: str, mode: str = "normal"):
    """Called when the user activates or switches to a session."""
    global _current_session_id, _current_mode
    _current_session_id = session_id
    _current_mode = mode
    logger.info(f"[PRIVACY] Session={session_id}, Mode={mode}")


def get_mode() -> str:
    """Returns the current privacy mode."""
    return _current_mode


def get_session_id() -> str | None:
    """Returns the current active session ID."""
    return _current_session_id


def is_incognito() -> bool:
    """True if no data should be written to disk."""
    return _current_mode == "incognito"


def is_auto_wipe() -> bool:
    """True if data should be wiped when the session is cleared."""
    return _current_mode == "auto_wipe"


def get_privacy_config(cfg_manager=None) -> dict:
    """Reads privacy configuration from ConfigManager or returns defaults."""
    defaults = {
        "default_mode": "normal",
        "auto_wipe_on_clear": True,
        "wipe_messages": True,
        "wipe_profile": False,
        "wipe_context": False,
    }
    if cfg_manager is None:
        return defaults
    try:
        privacy = cfg_manager.config.get("privacy", {})
        return {**defaults, **privacy}
    except Exception:
        return defaults
