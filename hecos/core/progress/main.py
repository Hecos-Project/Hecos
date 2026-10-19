"""
hecos/core/progress/main.py
─────────────────────────────────────────────────────────────────────────────
ProgressManager — Central coordinator for Hecos progress tracking.
Manages tasks, dispatches updates to sinks (Rich/ANSI CLI, Logger, WebUI SSE),
handles task cancellation and provides context managers and convenience helpers.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional, Any
from contextlib import contextmanager

from hecos.core.progress.model import Task, Phase, CancellationRequested
from hecos.core.progress.sinks import CliRichSink, LoggerSink, WebUiSink


_thread_local = threading.local()


def current_task() -> Optional[Task]:
    """Return the active Task for the current thread, if any."""
    return getattr(_thread_local, "current_task", None)


class TaskContext:
    """Context manager wrapper around a Task to handle auto-completion and error catching."""
    def __init__(self, manager: ProgressManager, task: Task):
        self.manager = manager
        self.task = task
        self._prev_task: Optional[Task] = None

    def __enter__(self) -> Task:
        self._prev_task = getattr(_thread_local, "current_task", None)
        _thread_local.current_task = self.task
        self.manager.register_task(self.task)
        self.manager.notify(self.task)
        return self.task

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type is None:
                if self.task.state not in ("done", "error", "cancelled"):
                    self.task.done()
                self.manager.notify(self.task)
                return True
            elif issubclass(exc_type, CancellationRequested):
                self.task.cancel()
                self.manager.notify(self.task)
                # Gracefully handle cancellation exit without crashing caller
                return True
            else:
                self.task.fail(str(exc_val))
                self.manager.notify(self.task)
                # Re-raise unexpected exceptions
                return False
        finally:
            _thread_local.current_task = self._prev_task


class ProgressManager:
    def __init__(self):
        self._tasks: Dict[str, Task] = {}
        self._history: List[Task] = []
        self._lock = threading.RLock()

        # Initialize sinks
        self.cli_sink = CliRichSink()
        self.logger_sink = LoggerSink()
        self.webui_sink = WebUiSink()

        self._sinks = [self.cli_sink, self.logger_sink, self.webui_sink]

    def register_task(self, task: Task) -> None:
        with self._lock:
            self._tasks[task.id] = task

    def get_task(self, task_id: str) -> Optional[Task]:
        with self._lock:
            if task_id in self._tasks:
                return self._tasks[task_id]
            for t in reversed(self._history):
                if t.id == task_id:
                    return t
        return None

    def cancel_task(self, task_id: str, reason: str = "Annullato dall'utente.") -> bool:
        """Requests cancellation of an active task."""
        with self._lock:
            task = self._tasks.get(task_id)
            if task and task.cancellable and task.state in ("pending", "running"):
                task.cancel(reason)
                self.notify(task)
                return True
        return False

    def list_active(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [t.to_dict() for t in self._tasks.values() if t.state in ("pending", "running")]

    def list_recent(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            all_tasks = list(self._tasks.values()) + list(self._history)
            # Deduplicate by id preserving most recent
            seen = set()
            res = []
            for t in reversed(all_tasks):
                if t.id not in seen:
                    seen.add(t.id)
                    res.append(t.to_dict())
                if len(res) >= limit:
                    break
            return res

    def notify(self, task: Task) -> None:
        """Dispatches task updates to all registered sinks."""
        # Check if task reached terminal state -> archive
        if task.state in ("done", "error", "cancelled"):
            with self._lock:
                if task.id in self._tasks:
                    self._tasks.pop(task.id, None)
                    self._history.append(task)
                    if len(self._history) > 30:
                        self._history.pop(0)

        for sink in self._sinks:
            try:
                sink.update(task)
            except Exception:
                pass

    def task(
        self,
        task_id: str,
        title: str,
        source: str = "SYSTEM",
        phases: Optional[List[tuple[str, float] | Phase | str]] = None,
        cancellable: bool = True,
        on_cancel: Optional[callable] = None,
    ) -> TaskContext:
        """
        Creates a new progress task context manager.
        Usage:
            with progress.task("my_id", "Downloading...", source="HPM", phases=[...]) as t:
                t.advance(...)
        """
        # Hook up task notification on advances
        t = Task(
            task_id=task_id,
            title=title,
            source=source,
            phases=phases,
            cancellable=cancellable,
            on_cancel=on_cancel,
        )

        original_advance = t.advance
        original_phase = t.phase

        def _notifying_advance(*args, **kwargs):
            res = original_advance(*args, **kwargs)
            self.notify(t)
            return res

        def _notifying_phase(*args, **kwargs):
            res = original_phase(*args, **kwargs)
            self.notify(t)
            return res

        t.advance = _notifying_advance
        t.phase = _notifying_phase

        return TaskContext(self, t)

    # Convenience wrappers
    def download(self, url: str, dest_path: str, task: Optional[Task] = None, **kwargs) -> str:
        from hecos.core.progress.adapters.download import download_file
        return download_file(url, dest_path, task=task, **kwargs)

    def pip(self, pip_args: List[str], task: Optional[Task] = None, **kwargs):
        from hecos.core.progress.adapters.pip import run_pip
        return run_pip(pip_args, task=task, **kwargs)

    def track(self, iterable, task: Optional[Task] = None, **kwargs):
        from hecos.core.progress.adapters.iterable import track as it_track
        return it_track(iterable, task=task, **kwargs)


# Global singleton
_manager_instance: Optional[ProgressManager] = None
_manager_lock = threading.Lock()


def get_progress_manager() -> ProgressManager:
    global _manager_instance
    if _manager_instance is None:
        with _manager_lock:
            if _manager_instance is None:
                _manager_instance = ProgressManager()
    return _manager_instance
