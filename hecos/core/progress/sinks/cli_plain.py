"""
hecos/core/progress/sinks/cli_plain.py
─────────────────────────────────────────────────────────────────────────────
Plain console progress sink.
Works without any external dependencies (stdlib only).
Handles both interactive ANSI terminals and headless log redirections cleanly.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import sys
import time
from typing import Optional
from hecos.core.progress.model import Task

# ANSI codes
_RESET  = "\033[0m"
_CYAN   = "\033[96m"
_GREEN  = "\033[92m"
_YELLOW = "\033[93m"
_RED    = "\033[91m"
_DIM    = "\033[2m"
_BOLD   = "\033[1m"


class CliPlainSink:
    def __init__(self, stream=None):
        self.stream = stream or sys.stdout
        self.is_tty = hasattr(self.stream, "isatty") and self.stream.isatty()
        self._last_print_time = 0.0
        self._last_logged_pct = -10.0
        self._last_phase_key = None

    def _format_bytes(self, b: int) -> str:
        if b < 1024:
            return f"{b} B"
        elif b < 1024 * 1024:
            return f"{b / 1024:.1f} KB"
        elif b < 1024 * 1024 * 1024:
            return f"{b / (1024 * 1024):.1f} MB"
        return f"{b / (1024 * 1024 * 1024):.2f} GB"

    def update(self, task: Task) -> None:
        now = time.time()
        pct = task.overall_percent()
        curr_phase = task.current_phase
        phase_key = curr_phase.key if curr_phase else None

        # Determine if we should print
        phase_changed = phase_key != self._last_phase_key
        is_terminal_state = task.state in ("done", "error", "cancelled")
        time_elapsed = (now - self._last_print_time) >= 0.15

        if self.is_tty:
            if not (time_elapsed or phase_changed or is_terminal_state):
                return
            self._last_print_time = now
            self._last_phase_key = phase_key

            width = 24
            filled = int((pct / 100.0) * width)
            empty = width - filled
            bar = f"{_CYAN}{'█' * filled}{_DIM}{'░' * empty}{_RESET}"

            extra = ""
            if task.bytes_total > 0:
                extra = f" [{self._format_bytes(task.bytes_done)} / {self._format_bytes(task.bytes_total)}]"
                if task.speed_bps > 0:
                    extra += f" @ {self._format_bytes(int(task.speed_bps))}/s"
                if task.eta_s is not None and task.eta_s > 0:
                    extra += f" ETA {int(task.eta_s)}s"

            msg = task.message or (curr_phase.label if curr_phase else "")
            if len(msg) > 35:
                msg = msg[:32] + "..."

            if is_terminal_state:
                color = _GREEN if task.state == "done" else _RED
                symbol = "✓" if task.state == "done" else "✗"
                line = f"\r{color}[{task.source}] {symbol} {task.title}: {task.state.upper()} ({pct:.0f}%){_RESET} - {msg}{' '*15}\n"
                self.stream.write(line)
                self.stream.flush()
            else:
                line = f"\r{_BOLD}[{task.source}]{_RESET} {task.title[:20]}: {bar} {pct:4.1f}%{extra} {msg}"
                self.stream.write(line)
                self.stream.flush()
        else:
            # Non-interactive / file redirection mode:
            # Print on phase change, every 10% step, or on finish
            should_log = (
                phase_changed or
                is_terminal_state or
                (pct - self._last_logged_pct >= 10.0 and now - self._last_print_time >= 3.0)
            )
            if not should_log:
                return

            self._last_print_time = now
            self._last_logged_pct = pct
            self._last_phase_key = phase_key

            msg = task.message or (curr_phase.label if curr_phase else "")
            if is_terminal_state:
                self.stream.write(f"[{task.source}] {task.title} -> {task.state.upper()} ({pct:.0f}%): {msg}\n")
            else:
                extra = ""
                if task.bytes_total > 0:
                    extra = f" ({self._format_bytes(task.bytes_done)}/{self._format_bytes(task.bytes_total)})"
                self.stream.write(f"[{task.source}] {task.title} [{pct:.1f}%]{extra} - {msg}\n")
            self.stream.flush()
