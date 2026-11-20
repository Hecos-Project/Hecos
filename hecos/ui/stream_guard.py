"""
hecos/ui/stream_guard.py
Intercepts stray writes to stdout/stderr from background threads, external libraries,
and progress bars (tqdm, HuggingFace Hub, LiteLLM), routing them safely into Zone 2 (Body)
or suppressing/logging them to prevent terminal UI corruption.
"""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING, Any

from hecos.ui.ansi import strip_ansi

if TYPE_CHECKING:
    from hecos.ui.viewport import TerminalViewport

_STDERR_NOISE_PATTERNS = (
    "Loading weights:",
    "it/s]",
    "s/it]",
    "unauthenticated requests to the HF Hub",
    "HF_TOKEN",
    "LiteLLM:",
    "Creating AiohttpTransport",
    "Using AiohttpTransport",
    "Creating new ClientSession",
    "127.0.0.1 - - [",
    "WARNING: This is a development server",
    "Press CTRL+C to quit",
    "UserWarning:",
    "FutureWarning:",
    "DeprecationWarning:",
)


class ConsoleStreamGuard:
    """
    File-like proxy installed on `sys.stdout` and `sys.stderr` while the 3-zone
    TUI is active:
      - `stdout` writes from legacy `print()` calls are buffered by line and
        cleanly routed into Zone 2 (`viewport.print_body`).
      - `stderr` progress bars (`\\r` tqdm) and third-party library noise are
        suppressed from the terminal and logged quietly to disk; genuine fatal
        tracebacks are surfaced cleanly in Zone 2 without breaking the layout.
    """

    def __init__(self, wrapped: Any, viewport: "TerminalViewport", is_stderr: bool = False):
        self._wrapped = wrapped
        self._viewport = viewport
        self._is_stderr = is_stderr
        self._buf = ""
        self._local = threading.local()

    @property
    def wrapped(self) -> Any:
        return self._wrapped

    def write(self, data: str) -> int:
        if not data:
            return 0
        if not isinstance(data, str):
            data = str(data)

        # Pass directly to raw stream when TUI is inactive, in modal menu, or re-entrant
        if (
            not self._viewport.is_active
            or self._viewport.is_modal
            or getattr(self._local, "busy", False)
        ):
            return self._wrapped.write(data)

        self._local.busy = True
        try:
            if self._is_stderr:
                self._handle_stderr(data)
            else:
                self._handle_stdout(data)
            return len(data)
        finally:
            self._local.busy = False

    def _handle_stdout(self, data: str) -> None:
        # Ignore bare carriage-return line-clearing hacks (e.g. "\r" + " "*80 + "\r")
        if "\n" not in data and "\r" in data:
            stripped = strip_ansi(data).replace("\r", "").strip()
            if not stripped:
                return

        self._buf += data
        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            line = line.rstrip("\r")
            # Handle embedded \r overwrites within a single line (keep final segment)
            if "\r" in line:
                segments = [seg for seg in line.split("\r") if seg]
                line = segments[-1] if segments else ""
            self._viewport.print_body(line)

    def _handle_stderr(self, data: str) -> None:
        # Pure carriage-return progress updates (tqdm without \n) -> drop from screen
        if "\n" not in data and "\r" in data:
            return

        self._buf += data
        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            line = line.rstrip("\r")
            if "\r" in line:
                segments = [seg for seg in line.split("\r") if seg.strip()]
                line = segments[-1] if segments else ""

            clean = strip_ansi(line).strip()
            if not clean:
                continue

            # Forward silently to debug log file if available
            self._log_stderr_silently(clean)

            # Never let third-party library chatter touch the TUI screen
            if any(pat in clean for pat in _STDERR_NOISE_PATTERNS):
                continue
            # Ignore tqdm block-bar lines
            if any(bar_ch in clean for bar_ch in ("██", "▏", "▎", "▍", "▌", "▋", "▊", "▉")):
                continue

            # Only surface genuine unhandled Python tracebacks/fatal errors in Zone 2
            if clean.startswith(
                ("Traceback (most recent call last):", "FATAL ERROR", "RuntimeError:", "SyntaxError:")
            ):
                self._viewport.print_body(f"\033[91m[STDERR] {clean}\033[0m")

    @staticmethod
    def _log_stderr_silently(clean_line: str) -> None:
        try:
            from hecos.core.logging.logger import debug_file_handler
            rec = logging.LogRecord(
                name="stderr.capture",
                level=logging.DEBUG,
                pathname="",
                lineno=0,
                msg=f"[STDERR] {clean_line}",
                args=(),
                exc_info=None,
            )
            debug_file_handler.emit(rec)
        except Exception:
            pass

    def flush(self) -> None:
        if not self._viewport.is_active or self._viewport.is_modal:
            try:
                self._wrapped.flush()
            except Exception:
                pass

    def isatty(self) -> bool:
        try:
            return self._wrapped.isatty()
        except Exception:
            return False

    def fileno(self) -> int:
        return self._wrapped.fileno()

    @property
    def encoding(self) -> str:
        return getattr(self._wrapped, "encoding", "utf-8")

    @property
    def errors(self) -> str:
        return getattr(self._wrapped, "errors", "replace")

    def reconfigure(self, *args, **kwargs):
        if hasattr(self._wrapped, "reconfigure"):
            return self._wrapped.reconfigure(*args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._wrapped, name)

