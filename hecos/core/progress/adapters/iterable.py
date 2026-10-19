"""
hecos/core/progress/adapters/iterable.py
─────────────────────────────────────────────────────────────────────────────
Iterable tracking adapter.
Provides a track() generator similar to tqdm / rich.progress.track,
yielding elements while advancing task metrics.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

from typing import Iterable, TypeVar, Optional
from hecos.core.progress.model import Task

T = TypeVar("T")


def track(
    sequence: Iterable[T],
    task: Optional[Task] = None,
    total: Optional[int] = None,
    description: Optional[str] = None,
) -> Iterable[T]:
    """
    Wraps an iterable and updates the given task for each item yielded.
    Supports cancellation check on every iteration.
    """
    if total is None:
        try:
            total = len(sequence)  # type: ignore
        except (TypeError, AttributeError):
            total = 0

    if task and description:
        task.advance(message=description)

    count = 0
    for item in sequence:
        if task:
            task.check_cancelled()
            count += 1
            task.advance(delta_bytes=1, total_bytes=total if total > 0 else None)
        yield item
