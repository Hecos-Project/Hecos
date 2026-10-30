"""
hecos/core/progress/sinks/logger_sink.py
─────────────────────────────────────────────────────────────────────────────
Logs milestone progress events with visual text bars to the central Hecos Logger.
Appears cleanly in the Hecos logs viewer and log files.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import time
from typing import Dict, Any, Optional
from hecos.core.progress.model import Task
from hecos.core.logging import logger


def _render_bar(pct: float, width: int = 20) -> str:
    clamped = max(0.0, min(100.0, pct))
    filled = int(round((clamped / 100.0) * width))
    empty = width - filled
    return f"[{'█' * filled}{'░' * empty}]"


def _format_bytes(b: int) -> str:
    if b < 1024:
        return f"{b} B"
    elif b < 1024 * 1024:
        return f"{b / 1024:.1f} KB"
    elif b < 1024 * 1024 * 1024:
        return f"{b / (1024 * 1024):.1f} MB"
    return f"{b / (1024 * 1024 * 1024):.2f} GB"


class LoggerSink:
    def __init__(self, bar_width: int = 20, step_pct: float = 10.0, min_interval_s: float = 1.5):
        self.bar_width = bar_width
        self.step_pct = step_pct
        self.min_interval_s = min_interval_s
        self._last_phase: Dict[str, Optional[str]] = {}
        self._last_logged_pct: Dict[str, float] = {}
        self._last_logged_time: Dict[str, float] = {}
        self._started: Dict[str, bool] = {}

    def update(self, task: Task) -> None:
        now = time.time()
        pct = task.overall_percent()
        curr_phase = task.current_phase
        phase_key = curr_phase.key if curr_phase else None

        # 1. On task start
        if task.id not in self._started:
            self._started[task.id] = True
            self._last_logged_time[task.id] = now
            self._last_logged_pct[task.id] = 0.0
            self._last_phase[task.id] = phase_key
            bar = _render_bar(0.0, self.bar_width)
            logger.info(task.source, f"Operation started: {task.title} {bar}   0.0%")

        # 2. Terminal states
        if task.state == "done":
            bar = _render_bar(100.0, self.bar_width)
            msg = f" - {task.message}" if task.message else ""
            logger.info(task.source, f"Completed successfully: {task.title} {bar} 100.0%{msg}")
            self._cleanup(task.id)
            return
        elif task.state == "cancelled":
            bar = _render_bar(pct, self.bar_width)
            logger.warning(task.source, f"Operation cancelled: {task.title} {bar} {pct:5.1f}%")
            self._cleanup(task.id)
            return
        elif task.state == "error":
            bar = _render_bar(pct, self.bar_width)
            logger.error(task.source, f"Error during '{task.title}' {bar} {pct:5.1f}%: {task.error}")
            self._cleanup(task.id)
            return

        # 3. Intermediate updates: trigger on phase change or step_pct advance with throttling
        phase_changed = phase_key != self._last_phase.get(task.id)
        pct_diff = pct - self._last_logged_pct.get(task.id, 0.0)
        time_diff = now - self._last_logged_time.get(task.id, 0.0)

        should_log = phase_changed or (pct_diff >= self.step_pct and time_diff >= self.min_interval_s)

        if should_log:
            self._last_phase[task.id] = phase_key
            self._last_logged_pct[task.id] = pct
            self._last_logged_time[task.id] = now

            bar = _render_bar(pct, self.bar_width)
            parts = [f"[{task.title}] {bar} {pct:5.1f}%"]
            if task.bytes_total > 0:
                parts.append(f"({_format_bytes(task.bytes_done)} / {_format_bytes(task.bytes_total)})")
                if task.speed_bps > 0:
                    parts.append(f"@ {_format_bytes(int(task.speed_bps))}/s")
            if curr_phase:
                parts.append(f"- Phase: {curr_phase.label}")
                if curr_phase.message and curr_phase.message != curr_phase.label:
                    parts.append(f"({curr_phase.message})")
            elif task.message:
                parts.append(f"- {task.message}")

            logger.info(task.source, " ".join(parts))

    def _cleanup(self, task_id: str):
        self._last_phase.pop(task_id, None)
        self._last_logged_pct.pop(task_id, None)
        self._last_logged_time.pop(task_id, None)
        self._started.pop(task_id, None)
