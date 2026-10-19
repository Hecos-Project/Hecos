"""
hecos/core/progress/sinks/cli_rich.py
─────────────────────────────────────────────────────────────────────────────
Rich CLI Progress Sink.
Provides rich, animated terminal bars with colors, speed, ETA, and phases.
Automatically falls back to CliPlainSink if Rich is unavailable or terminal is non-TTY.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import sys
import threading
from typing import Dict, Optional, Any
from hecos.core.progress.model import Task
from .cli_plain import CliPlainSink


class CliRichSink:
    def __init__(self):
        self._lock = threading.Lock()
        self._rich_progress = None
        self._task_map: Dict[str, Any] = {}
        self._fallback = CliPlainSink()
        self._use_fallback = False

        if not (hasattr(sys.stdout, "isatty") and sys.stdout.isatty()):
            self._use_fallback = True

    def _ensure_rich(self):
        if self._use_fallback:
            return None
        if self._rich_progress is not None:
            return self._rich_progress

        try:
            from rich.progress import (
                Progress,
                SpinnerColumn,
                TextColumn,
                BarColumn,
                TaskProgressColumn,
                DownloadColumn,
                TransferSpeedColumn,
                TimeRemainingColumn,
            )
            from rich.console import Console

            console = Console(file=sys.stdout)
            self._rich_progress = Progress(
                SpinnerColumn(spinner_name="dots"),
                TextColumn("[bold cyan][{task.fields[source]}][/]"),
                TextColumn("[bold white]{task.description}"),
                BarColumn(bar_width=24, complete_style="green", finished_style="bold green"),
                TaskProgressColumn(),
                DownloadColumn(),
                TransferSpeedColumn(),
                TimeRemainingColumn(),
                TextColumn("[dim]{task.fields[message]}[/]"),
                console=console,
                auto_refresh=True,
                transient=False,
            )
            self._rich_progress.start()
            return self._rich_progress
        except Exception:
            self._use_fallback = True
            return None

    def update(self, task: Task) -> None:
        with self._lock:
            if self._use_fallback:
                self._fallback.update(task)
                return

            rp = self._ensure_rich()
            if not rp:
                self._fallback.update(task)
                return

            try:
                curr_phase = task.current_phase
                msg = task.message or (curr_phase.label if curr_phase else "")
                if len(msg) > 30:
                    msg = msg[:28] + "…"

                if task.id not in self._task_map:
                    # New task in rich
                    rich_id = rp.add_task(
                        description=task.title[:24],
                        total=task.bytes_total if task.bytes_total > 0 else 100,
                        completed=task.bytes_done if task.bytes_total > 0 else task.overall_percent(),
                        source=task.source,
                        message=msg,
                    )
                    self._task_map[task.id] = rich_id
                else:
                    rich_id = self._task_map[task.id]
                    if task.bytes_total > 0:
                        rp.update(
                            rich_id,
                            total=task.bytes_total,
                            completed=task.bytes_done,
                            message=msg,
                        )
                    else:
                        rp.update(
                            rich_id,
                            total=100.0,
                            completed=task.overall_percent(),
                            message=msg,
                        )

                if task.state in ("done", "error", "cancelled"):
                    if task.state == "done":
                        rp.update(rich_id, completed=task.bytes_total or 100.0, message="✓ Fatto")
                    elif task.state == "cancelled":
                        rp.update(rich_id, message="⊘ Annullato")
                    else:
                        rp.update(rich_id, message=f"✗ {task.error or 'Errore'}")

                    # Remove from active map so final line stays printed
                    self._task_map.pop(task.id, None)
                    if not self._task_map:
                        rp.stop()
                        self._rich_progress = None
            except Exception:
                self._use_fallback = True
                self._fallback.update(task)

    def close(self):
        with self._lock:
            if self._rich_progress is not None:
                try:
                    self._rich_progress.stop()
                except Exception:
                    pass
                self._rich_progress = None
