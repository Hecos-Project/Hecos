"""
hecos/core/progress
─────────────────────────────────────────────────────────────────────────────
Unified progress tracking system for Hecos.
Provides consistent progress bars, phases, speed/ETA metrics, and cancellation
across CLI (Rich/ANSI) and WebUI (SSE).
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

from .model import Task, Phase, CancellationRequested
from .main import ProgressManager, get_progress_manager

# Global convenience accessor
class _ProgressProxy:
    def __getattr__(self, name):
        return getattr(get_progress_manager(), name)

    def task(self, *args, **kwargs):
        return get_progress_manager().task(*args, **kwargs)

    def download(self, *args, **kwargs):
        return get_progress_manager().download(*args, **kwargs)

    def pip(self, *args, **kwargs):
        return get_progress_manager().pip(*args, **kwargs)

    def track(self, *args, **kwargs):
        return get_progress_manager().track(*args, **kwargs)

    def cancel(self, task_id: str, reason: str = "Annullato dall'utente."):
        return get_progress_manager().cancel_task(task_id, reason=reason)


progress = _ProgressProxy()

__all__ = [
    "progress",
    "ProgressManager",
    "Task",
    "Phase",
    "CancellationRequested",
    "get_progress_manager",
]
