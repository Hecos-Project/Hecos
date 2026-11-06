"""
Hecos Presenter - Core Engine
Coordinates lifecycle, event bus subscriptions, and delegates event processing.
"""

import threading
from typing import Dict, Any

from hecos.core.logging import logger
from hecos.core.events import bus
from hecos.modules.web_ui.extensions.presenter.config.store import load_presenter_config
from hecos.modules.web_ui.extensions.presenter.engine_commentary import generate_presenter_commentary
from hecos.modules.web_ui.extensions.presenter.engine_events import PresenterEventHandler


class PresenterEngine:
    def __init__(self):
        self._running = False
        self._lock = threading.Lock()
        self._events = PresenterEventHandler(self)

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def cfg(self):
        return load_presenter_config()

    def start(self):
        with self._lock:
            if self._running:
                return
            self._running = True

            # Subscribe to event bus
            bus.subscribe("persona_switched", self._on_persona_switched)
            bus.subscribe("new_chat", self._on_new_chat)
            bus.subscribe("message_exchange", self._on_message_exchange)
            bus.subscribe("user_message_sent", self._on_user_message_sent)
            bus.subscribe("assistant_response", self._on_assistant_response)
            bus.subscribe("progress", self._on_progress_event)
            bus.subscribe("search_started", self._on_search_started)
            bus.subscribe("search_completed", self._on_search_completed)
            logger.info("[Presenter] Engine started. Subscribed to events (including search).")

    def _generate_commentary(self, event_type: str, system_prompt: str, user_prompt: str, session_id: str = None):
        """Generates commentary using the designated Global Preset model."""
        generate_presenter_commentary(self.cfg, event_type, system_prompt, user_prompt, session_id=session_id)

    # ── Delegating Event Handlers (Backward Compatibility) ────────────

    def _on_persona_switched(self, event: Dict[str, Any]):
        self._events.on_persona_switched(event)

    def _on_new_chat(self, event: Dict[str, Any]):
        self._events.on_new_chat(event)

    def _on_search_started(self, event: Dict[str, Any]):
        self._events.on_search_started(event)

    def _on_search_completed(self, event: Dict[str, Any]):
        self._events.on_search_completed(event)

    def _on_package_event(self, event: Dict[str, Any]):
        self._events.on_package_event(event)

    def _on_progress_event(self, event: Dict[str, Any]):
        self._events.on_progress_event(event)

    def _on_user_message_sent(self, event: Dict[str, Any]):
        self._events.on_user_message_sent(event)

    def _on_assistant_response(self, event: Dict[str, Any]):
        self._events.on_assistant_response(event)

    def _on_message_exchange(self, event: Dict[str, Any]):
        self._events.on_message_exchange(event)


_engine_instance = None


def get_engine() -> PresenterEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = PresenterEngine()
    return _engine_instance
