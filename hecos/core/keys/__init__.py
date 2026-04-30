"""
core/keys — API Key Pool Manager for Hecos.

Public API:
    from hecos.core.keys import get_key_manager
    km = get_key_manager()
    key = km.get_key("groq")
"""

from hecos.core.keys.key_manager import KeyManager, get_key_manager

__all__ = ["KeyManager", "get_key_manager"]
