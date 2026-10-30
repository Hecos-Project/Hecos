"""
hecos/core/progress/model.py
─────────────────────────────────────────────────────────────────────────────
Data models and calculations for the unified Hecos progress tracking system.
Handles phases, weighted progress, byte accounting, EMA speed, and ETA estimation.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


class CancellationRequested(Exception):
    """Raised when an active progress task has been cancelled by user or system."""
    pass


@dataclass
class Phase:
    key: str
    label: str
    weight: float = 1.0
    percent: float = 0.0
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "weight": round(self.weight, 2),
            "percent": round(self.percent, 1),
            "message": self.message,
        }


class Task:
    def __init__(
        self,
        task_id: str,
        title: str,
        source: str = "SYSTEM",
        phases: Optional[List[tuple[str, float] | Phase | str]] = None,
        cancellable: bool = True,
        on_cancel: Optional[callable] = None,
    ):
        self.id = task_id
        self.title = title
        self.source = source
        self.cancellable = cancellable
        self.on_cancel = on_cancel

        self.state = "pending"  # "pending", "running", "done", "error", "cancelled"
        self.message = ""
        self.log = ""
        self.error: Optional[str] = None

        self.bytes_done: int = 0
        self.bytes_total: int = 0
        self.speed_bps: float = 0.0
        self.eta_s: Optional[float] = None

        self._cancelled = False
        self.start_time: float = time.time()
        self.end_time: Optional[float] = None
        self.last_update_time: float = self.start_time

        # EMA speed tracking
        self._last_ema_time: float = self.start_time
        self._last_ema_bytes: int = 0
        self._ema_alpha: float = 0.25

        # Initialize phases
        self.phases: List[Phase] = []
        if phases:
            for p in phases:
                if isinstance(p, Phase):
                    self.phases.append(p)
                elif isinstance(p, tuple):
                    key = str(p[0])
                    if len(p) == 2:
                        if isinstance(p[1], (int, float)):
                            weight = float(p[1])
                            label = key.replace("_", " ").title()
                        else:
                            weight = 1.0
                            label = str(p[1])
                    elif len(p) >= 3:
                        if isinstance(p[1], (int, float)):
                            weight = float(p[1])
                            label = str(p[2])
                        else:
                            label = str(p[1])
                            weight = float(p[2])
                    else:
                        weight = 1.0
                        label = key.replace("_", " ").title()
                    self.phases.append(Phase(key=key, label=label, weight=weight))
                elif isinstance(p, str):
                    self.phases.append(Phase(key=p, label=p.replace("_", " ").title(), weight=1.0))

        self.current_phase_idx: int = 0 if self.phases else -1
        self._flat_percent: float = 0.0

    @property
    def current_phase(self) -> Optional[Phase]:
        if 0 <= self.current_phase_idx < len(self.phases):
            return self.phases[self.current_phase_idx]
        return None

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled

    def cancel(self, reason: str = "Operation cancelled by user.") -> None:
        """Mark this task as cancelled and call cancel handler if registered."""
        self._cancelled = True
        self.state = "cancelled"
        self.message = reason
        self.end_time = time.time()
        if self.on_cancel:
            try:
                self.on_cancel()
            except Exception:
                pass

    def check_cancelled(self) -> None:
        """Helper to be called inside loops to interrupt work promptly."""
        if self._cancelled:
            raise CancellationRequested(f"Task '{self.id}' was cancelled.")

    def phase(self, key_or_idx: str | int, message: Optional[str] = None, label: Optional[str] = None) -> Phase:
        """Advance to a named phase or phase index."""
        self.check_cancelled()
        if self.state == "pending":
            self.state = "running"

        target_idx = -1
        if isinstance(key_or_idx, int):
            target_idx = key_or_idx
        else:
            for idx, p in enumerate(self.phases):
                if p.key == key_or_idx:
                    target_idx = idx
                    break

        if target_idx != -1 and target_idx < len(self.phases):
            # Mark prior phases as 100%
            for i in range(target_idx):
                self.phases[i].percent = 100.0
            self.current_phase_idx = target_idx
            curr = self.phases[target_idx]
            if label:
                curr.label = label
            if message is not None:
                curr.message = message
                self.message = message
            return curr

        # If phase not pre-declared, create dynamically
        key = str(key_or_idx)
        dyn_label = label or key.replace("_", " ").title()
        new_phase = Phase(key=key, label=dyn_label, weight=1.0, message=message or "")
        self.phases.append(new_phase)
        self.current_phase_idx = len(self.phases) - 1
        if message is not None:
            self.message = message
        return new_phase

    def advance(
        self,
        delta_bytes: int = 0,
        bytes_done: Optional[int] = None,
        total_bytes: Optional[int] = None,
        percent: Optional[float] = None,
        message: Optional[str] = None,
        log: Optional[str] = None,
    ) -> None:
        """Advance progress metrics (bytes, percent, message, speed, ETA)."""
        self.check_cancelled()
        if self.state == "pending":
            self.state = "running"

        now = time.time()
        if message is not None:
            self.message = message
            if self.current_phase:
                self.current_phase.message = message
        if log is not None:
            self.log = log

        # Update byte counts
        if total_bytes is not None:
            self.bytes_total = max(0, total_bytes)
        if bytes_done is not None:
            self.bytes_done = max(0, bytes_done)
        elif delta_bytes > 0:
            self.bytes_done += delta_bytes

        # Update percent
        if percent is not None:
            computed_pct = max(0.0, min(100.0, float(percent)))
        elif self.bytes_total > 0:
            computed_pct = max(0.0, min(100.0, (self.bytes_done / self.bytes_total) * 100.0))
        else:
            computed_pct = None

        if computed_pct is not None:
            if self.current_phase:
                self.current_phase.percent = computed_pct
            else:
                self._flat_percent = computed_pct

        # Update speed and ETA using Exponential Moving Average
        dt = now - self._last_ema_time
        if dt >= 0.25:  # update speed every 250ms minimum
            d_bytes = self.bytes_done - self._last_ema_bytes
            if d_bytes > 0:
                inst_speed = d_bytes / dt
                if self.speed_bps <= 0:
                    self.speed_bps = inst_speed
                else:
                    self.speed_bps = (self._ema_alpha * inst_speed) + ((1.0 - self._ema_alpha) * self.speed_bps)

                if self.bytes_total > self.bytes_done and self.speed_bps > 0:
                    remaining = self.bytes_total - self.bytes_done
                    self.eta_s = round(remaining / self.speed_bps, 1)
            self._last_ema_time = now
            self._last_ema_bytes = self.bytes_done

        self.last_update_time = now

    def done(self, message: Optional[str] = None) -> None:
        """Complete the task successfully (100%)."""
        self.state = "done"
        self.end_time = time.time()
        for p in self.phases:
            p.percent = 100.0
        self._flat_percent = 100.0
        if message:
            self.message = message
        if self.bytes_total > 0:
            self.bytes_done = self.bytes_total
        self.eta_s = 0.0

    def fail(self, error: str) -> None:
        """Mark task as failed with error details."""
        self.state = "error"
        self.end_time = time.time()
        self.error = str(error)
        self.message = str(error)

    def overall_percent(self) -> float:
        """Calculates global percentage (0.0 - 100.0) weighted across phases."""
        if self.state == "done":
            return 100.0
        if not self.phases:
            return round(self._flat_percent, 1)

        total_weight = sum(p.weight for p in self.phases)
        if total_weight <= 0:
            return 0.0

        accum = 0.0
        for p in self.phases:
            accum += (p.percent / 100.0) * p.weight
        return round(min(100.0, max(0.0, (accum / total_weight) * 100.0)), 1)

    def to_dict(self) -> Dict[str, Any]:
        curr = self.current_phase
        phase_info = None
        if curr:
            phase_info = {
                "key": curr.key,
                "label": curr.label,
                "index": self.current_phase_idx + 1,
                "count": len(self.phases),
                "percent": round(curr.percent, 1),
                "message": curr.message,
            }

        return {
            "type": "progress",
            "id": self.id,
            "title": self.title,
            "source": self.source,
            "state": self.state,
            "percent": self.overall_percent(),
            "cancellable": self.cancellable,
            "is_cancelled": self._cancelled,
            "phase": phase_info,
            "phases": [p.to_dict() for p in self.phases] if self.phases else [],
            "message": self.message,
            "log": self.log,
            "bytes_done": self.bytes_done,
            "bytes_total": self.bytes_total,
            "speed_bps": round(self.speed_bps),
            "eta_s": self.eta_s,
            "error": self.error,
            "elapsed_s": round(time.time() - self.start_time, 1),
        }
