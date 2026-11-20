"""
hecos/modules/web_ui/chat_search
Dedicated modular Chat Search package (SQLite FTS5 + RAM Incognito scoping).
"""
from .routes import chat_search_bp

__all__ = ["chat_search_bp"]
