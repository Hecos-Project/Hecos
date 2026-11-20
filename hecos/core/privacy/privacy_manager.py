"""
MODULE: Privacy Manager
DESCRIPTION: Manages per-session privacy mode (normal, incognito).
             - normal: persisted in SQLite DB with full memory, RAG, and user identity.
             - incognito: RAM-only session (multi-turn works while open, vanishes on
               restart/delete), zero disk writes, no user identity/profile/long-term
               memory/RAG injected into LLM prompts.
"""

from hecos.core.logging import logger

# In-memory flag for the currently focused web session (does NOT persist across restarts)
_current_mode: str = "normal"  # "normal" | "incognito"
_current_session_id: str | None = None


def normalize_mode(mode: str | None) -> str:
    """Normalizes privacy mode values. Legacy 'auto_wipe' maps transparently to 'incognito'."""
    val = str(mode or "normal").strip().lower()
    if val in ("incognito", "auto_wipe"):
        return "incognito"
    return "normal"


def set_session(session_id: str, mode: str = "normal"):
    """Called when the user activates or switches to a session."""
    global _current_session_id, _current_mode
    norm = normalize_mode(mode)
    _current_session_id = session_id
    _current_mode = norm
    logger.info(f"[PRIVACY] Session={session_id}, Mode={norm}")


def get_mode() -> str:
    """Returns the current privacy mode ('normal' or 'incognito')."""
    return _current_mode


def get_session_id() -> str | None:
    """Returns the current active session ID."""
    return _current_session_id


def is_incognito() -> bool:
    """True if the currently active session is in Incognito mode."""
    return _current_mode == "incognito"


def is_session_incognito(session_id: str | None = None) -> bool:
    """
    Session-accurate incognito check (safe with concurrent/background sessions).
    - If `session_id` is provided: returns True iff that session lives in RAM
      (_ram_sessions) or is the active session currently flagged incognito.
    - If `session_id` is omitted: falls back to global `_current_mode == 'incognito'`.
    """
    if session_id:
        try:
            from hecos.memory.session_state import _ram_sessions
            if session_id in _ram_sessions:
                return True
        except Exception:
            pass
        if _current_session_id is not None and session_id != _current_session_id:
            return False
    return _current_mode == "incognito"


def is_auto_wipe() -> bool:
    """Deprecated compatibility stub — 'auto_wipe' has been unified into 'incognito'."""
    return False


def get_privacy_config(cfg_manager=None) -> dict:
    """Reads privacy configuration from ConfigManager or returns defaults."""
    defaults = {
        "default_mode": "normal",
        "wipe_messages": True,
        "wipe_profile": False,
        "wipe_context": False,
    }
    if cfg_manager is None:
        return defaults
    try:
        privacy = cfg_manager.config.get("privacy", {})
        merged = {**defaults, **privacy}
        merged["default_mode"] = normalize_mode(merged.get("default_mode"))
        return merged
    except Exception:
        return defaults
