"""
hecos/core/progress/sinks/webui_sink.py
─────────────────────────────────────────────────────────────────────────────
WebUI Progress Sink.
Pushes progress updates to:
  1. WebUI StateManager (SSE stream /api/events)
  2. Core Event Bus (hecos.core.events.bus)
Includes rate limiting to protect network and browser DOM performance.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import time
from typing import Dict, Any
from hecos.core.progress.model import Task


class WebUiSink:
    def __init__(self, min_interval: float = 0.25):
        self.min_interval = min_interval  # max 4 updates/sec for smooth updates
        self._last_emit: Dict[str, float] = {}
        self._last_phase: Dict[str, str] = {}
        self._last_pct: Dict[str, float] = {}

    def update(self, task: Task) -> None:
        now = time.time()
        pct = task.overall_percent()
        curr_phase = task.current_phase
        phase_key = curr_phase.key if curr_phase else None

        is_terminal = task.state in ("done", "error", "cancelled")
        phase_changed = phase_key != self._last_phase.get(task.id)
        time_elapsed = (now - self._last_emit.get(task.id, 0.0)) >= self.min_interval

        # Don't throttle terminal events or phase switches
        if not (is_terminal or phase_changed or time_elapsed):
            return

        self._last_emit[task.id] = now
        self._last_phase[task.id] = phase_key or ""
        self._last_pct[task.id] = pct

        payload = task.to_dict()

        # 1. Dispatch via StateManager SSE
        try:
            from hecos.modules.web_ui.server import get_state_manager
            sm = get_state_manager()
            if sm is not None:
                sm.add_event("progress", payload)
        except Exception:
            pass

        # 2. Dispatch via Core Event Bus
        try:
            from hecos.core.events import bus
            bus.emit("progress", payload)
            if is_terminal:
                bus.emit(f"progress:{task.state}", payload)
        except Exception:
            pass

        if is_terminal:
            self._last_emit.pop(task.id, None)
            self._last_phase.pop(task.id, None)
            self._last_pct.pop(task.id, None)
