"""
history_manager.py
Handles storage and retrieval of chat input history for both CLI and WebUI.
"""

import os
import json
import threading

class InputHistoryManager:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if not cls._instance:
                cls._instance = super(InputHistoryManager, cls).__new__(cls)
                cls._instance._init()
            return cls._instance

    def _init(self):
        # We assume the caller or the application handles config separately or we can fetch it dynamically.
        # But to avoid circular imports, we just fetch it when needed.
        self.history_cache = {}  # { username: {"entries": [], "cursor": -1, "draft": ""} }
        self.data_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
            "data", "input_history"
        )
        os.makedirs(self.data_dir, exist_ok=True)
        self._cfg_mgr = None

    def _get_config(self):
        # Lazy load to avoid circular dependencies
        if not self._cfg_mgr:
            import sys
            if hasattr(sys, 'hecos_config_manager'):
                self._cfg_mgr = sys.hecos_config_manager
            else:
                from hecos.app.config import ConfigManager
                self._cfg_mgr = ConfigManager()
                
        # Default config if not present
        conf = self._cfg_mgr.config.get("input_history", {})
        return {
            "enabled": conf.get("enabled", True),
            "max_entries": conf.get("max_entries", 200),
            "persist": conf.get("persist", True),
            "deduplicate": conf.get("deduplicate", True)
        }

    def _get_file_path(self, user: str) -> str:
        safe_user = "".join(c for c in user if c.isalnum() or c in ("_", "-"))
        if not safe_user:
            safe_user = "admin"
        return os.path.join(self.data_dir, f"{safe_user}.json")

    def _load_user(self, user: str):
        if user not in self.history_cache:
            entries = []
            cfg = self._get_config()
            if cfg["persist"]:
                path = self._get_file_path(user)
                if os.path.exists(path):
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            if isinstance(data, list):
                                entries = data
                    except Exception as e:
                        from hecos.core.logging import logger
                        logger.error(f"[InputHistory] Failed to load history for {user}: {e}")
            self.history_cache[user] = {
                "entries": entries,
                "cursor": len(entries),
                "draft": ""
            }

    def _save_user(self, user: str):
        cfg = self._get_config()
        if not cfg["persist"]:
            return
            
        path = self._get_file_path(user)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.history_cache[user]["entries"], f, ensure_ascii=False, indent=2)
        except Exception as e:
            from hecos.core.logging import logger
            logger.error(f"[InputHistory] Failed to save history for {user}: {e}")

    def push(self, text: str, user: str = "admin"):
        cfg = self._get_config()
        if not cfg["enabled"]:
            return
            
        text = text.strip()
        if not text:
            return
            
        with self._lock:
            self._load_user(user)
            entries = self.history_cache[user]["entries"]
            
            # Deduplicate
            if cfg["deduplicate"] and entries and entries[-1] == text:
                self.reset_cursor(user)
                return
                
            entries.append(text)
            
            # Trim to max_entries
            max_entries = max(1, cfg["max_entries"])
            if len(entries) > max_entries:
                self.history_cache[user]["entries"] = entries[-max_entries:]
                
            self._save_user(user)
            self.reset_cursor(user)

    def navigate(self, direction: str, user: str = "admin", current_draft: str = "") -> str:
        """
        direction: "up" or "down"
        Returns the navigated string.
        """
        cfg = self._get_config()
        if not cfg["enabled"]:
            return current_draft
            
        with self._lock:
            self._load_user(user)
            state = self.history_cache[user]
            entries = state["entries"]
            
            if not entries:
                return current_draft
                
            # If we are at the very bottom, save the draft
            if state["cursor"] == len(entries):
                state["draft"] = current_draft
                
            if direction == "up":
                if state["cursor"] > 0:
                    state["cursor"] -= 1
            elif direction == "down":
                if state["cursor"] < len(entries):
                    state["cursor"] += 1
            
            if state["cursor"] == len(entries):
                return state["draft"]
            else:
                return entries[state["cursor"]]

    def reset_cursor(self, user: str = "admin"):
        with self._lock:
            self._load_user(user)
            self.history_cache[user]["cursor"] = len(self.history_cache[user]["entries"])
            self.history_cache[user]["draft"] = ""

    def get_all(self, user: str = "admin", limit: int = 50) -> list:
        cfg = self._get_config()
        if not cfg["enabled"]:
            return []
            
        with self._lock:
            self._load_user(user)
            return self.history_cache[user]["entries"][-limit:]

    def clear(self, user: str = "admin"):
        with self._lock:
            self.history_cache[user] = {
                "entries": [],
                "cursor": 0,
                "draft": ""
            }
            self._save_user(user)
