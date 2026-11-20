"""
hecos/ui/viewport.py
Native VT100 3-Zone Terminal Compositor for Hecos Console CLI.

Divides the terminal viewport (W x H) into three strictly isolated zones:
  - Zone 1 (Rows 1..5)     : Fixed Header (Version, F-keys, Status, Hardware, PTT/Divider)
  - Zone 2 (Rows 6..H-2)   : Scrollable Body via hardware DECSTBM (\\033[6;{H-2}r)
  - Zone 3 (Rows H-1..H)   : Fixed Footer (Separator on H-1, Input Prompt / Spinner on H)

Key guarantees:
  - Zero reliance on Colorama's legacy Win32 converter or fragile \\0337 / \\0338 save/restore.
  - All terminal writes are assembled into single atomic strings under an RLock.
  - Every Header or Body write explicitly parks the cursor back in Zone 3 (Row H).
  - Backward compatibility: re-exports ANSI and StreamGuard utilities.
"""

from __future__ import annotations

import atexit
import os
import shutil
import sys
import threading
from collections import deque
from typing import Deque, List, Optional, Tuple

# Re-export ANSI utilities for full backward compatibility
from hecos.ui.ansi import (
    ANSI_TOKEN_RE,
    HEADER_ROWS,
    FOOTER_ROWS,
    MIN_TERM_COLS,
    MIN_TERM_ROWS,
    strip_ansi,
    char_width as _char_width,
    visible_width,
    clip_ansi,
    wrap_ansi_line,
    enable_native_vt_console,
)
from hecos.ui.stream_guard import ConsoleStreamGuard

# Backward-compatible alias
_ANSI_TOKEN_RE = ANSI_TOKEN_RE


class TerminalViewport:
    """
    Thread-safe singleton compositor managing the 3-zone console layout.
    """

    def __init__(self):
        self._lock = threading.RLock()

        # Unwrap any existing guard to always hold the true underlying OS streams
        raw_out = sys.stdout
        while isinstance(raw_out, ConsoleStreamGuard):
            raw_out = raw_out.wrapped
        raw_err = sys.stderr
        while isinstance(raw_err, ConsoleStreamGuard):
            raw_err = raw_err.wrapped

        self._raw_stdout = raw_out
        self._raw_stderr = raw_err

        self._cols: int = 115
        self._rows: int = 30
        self._usable_width: int = 114

        self._active: bool = False
        self._modal: bool = False
        self._guards_installed: bool = False

        # Zone 1: 5 cached header rows
        self._header_cache: List[str] = [""] * HEADER_ROWS

        # Zone 2: logical body history (for resize & post-modal restoration)
        self._body_history: Deque[str] = deque(maxlen=300)
        self._body_row: int = HEADER_ROWS + 1
        self._body_bottom_occupied: bool = False

        # Zone 3: footer separator + input line editor / status override
        self._prompt_active: bool = False
        self._prompt_prefix: str = ""
        self._input_buffer: str = ""
        self._cursor_idx: int = 0
        self._view_offset: int = 0
        self._footer_override: Optional[str] = None
        self._footer_override_cursor: bool = False

    # ── Properties & Geometry ─────────────────────────────────────────────────

    @property
    def lock(self) -> threading.RLock:
        return self._lock

    @property
    def is_active(self) -> bool:
        return self._active

    @property
    def is_modal(self) -> bool:
        return self._modal

    @property
    def usable_width(self) -> int:
        return self._usable_width

    @property
    def cols(self) -> int:
        return self._cols

    @property
    def rows(self) -> int:
        return self._rows

    @property
    def body_top(self) -> int:
        return HEADER_ROWS + 1  # Row 6

    @property
    def body_bottom(self) -> int:
        return max(self.body_top + 1, self._rows - FOOTER_ROWS)

    @property
    def footer_sep_row(self) -> int:
        return max(self.body_bottom + 1, self._rows - 1)

    @property
    def prompt_row(self) -> int:
        return max(self.footer_sep_row + 1, self._rows)

    def _query_terminal_size(self) -> Tuple[int, int]:
        try:
            sz = shutil.get_terminal_size((115, 30))
            cols = max(MIN_TERM_COLS, sz.columns)
            rows = max(MIN_TERM_ROWS, sz.lines)
            return cols, rows
        except Exception:
            return (115, 30)

    def refresh_dimensions(self) -> bool:
        """Updates cached dimensions. Returns True if terminal size changed."""
        cols, rows = self._query_terminal_size()
        changed = (cols != self._cols) or (rows != self._rows)
        self._cols = cols
        self._rows = rows
        # Leave 1 column margin on the right to prevent auto-wrap / bottom-right scroll quirks
        self._usable_width = max(40, cols - 1)
        return changed

    # ── Lifecycle & Setup ─────────────────────────────────────────────────────

    def _can_use_tui(self) -> bool:
        if os.environ.get("HECOS_BOOT_MODE", "").lower() == "webui":
            return False
        try:
            return bool(self._raw_stdout and self._raw_stdout.isatty())
        except Exception:
            return False

    def install_stream_guards(self) -> None:
        if self._guards_installed:
            return
        if not isinstance(sys.stdout, ConsoleStreamGuard):
            sys.stdout = ConsoleStreamGuard(self._raw_stdout, self, is_stderr=False)
        if not isinstance(sys.stderr, ConsoleStreamGuard):
            sys.stderr = ConsoleStreamGuard(self._raw_stderr, self, is_stderr=True)
        self._guards_installed = True

    def setup(self, clear_history: bool = False) -> None:
        """Initializes native VT100 mode, stream guards, and the 3-zone screen layout."""
        with self._lock:
            enable_native_vt_console()
            try:
                if hasattr(self._raw_stdout, "reconfigure"):
                    self._raw_stdout.reconfigure(encoding="utf-8", errors="replace")
                if hasattr(self._raw_stderr, "reconfigure"):
                    self._raw_stderr.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

            self.refresh_dimensions()

            if clear_history:
                self._body_history.clear()

            if not self._can_use_tui():
                self._active = False
                return

            self.install_stream_guards()
            self._active = True
            self._modal = False
            self.full_redraw()

    def teardown(self) -> None:
        """Restores normal terminal state (scroll region, cursor, attributes, streams) on exit."""
        with self._lock:
            was_active = self._active
            self._active = False
            self._modal = False
            if self._guards_installed:
                if isinstance(sys.stdout, ConsoleStreamGuard):
                    sys.stdout = self._raw_stdout
                if isinstance(sys.stderr, ConsoleStreamGuard):
                    sys.stderr = self._raw_stderr
                self._guards_installed = False
            if was_active:
                try:
                    self._write_raw(f"\033[r\033[{self._rows};1H\033[0m\033[?25h\n")
                except Exception:
                    pass

    # ── Low-Level Atomic Output ───────────────────────────────────────────────

    def _write_raw(self, payload: str) -> None:
        if not payload:
            return
        self._raw_stdout.write(payload)
        self._raw_stdout.flush()

    def check_resize(self) -> bool:
        """If terminal dimensions changed, triggers a clean 3-zone full redraw."""
        with self._lock:
            if not self._active or self._modal:
                return False
            if self.refresh_dimensions():
                self.full_redraw()
                return True
            return False

    # ── Zone 3 (Footer & Cursor Parking) Builders ─────────────────────────────

    def _build_footer_seq(self) -> str:
        """Builds the ANSI sequence to render Zone 3 (Rows H-1..H) and park the cursor."""
        W = self._usable_width
        sep = f"\033[2m\033[36m{'─' * W}\033[0m"
        seq: List[str] = [f"\033[{self.footer_sep_row};1H\033[2K{sep}"]

        p_row = self.prompt_row
        if self._footer_override is not None:
            clipped = clip_ansi(self._footer_override, W)
            vis_w = visible_width(clipped)
            col = min(W + 1, max(1, vis_w + 1))
            cur_vis = "\033[?25h" if self._footer_override_cursor else "\033[?25l"
            seq.append(f"\033[{p_row};1H\033[2K{clipped}\033[{p_row};{col}H{cur_vis}")
            return "".join(seq)

        if not self._prompt_active:
            seq.append(f"\033[{p_row};1H\033[2K\033[{p_row};1H\033[?25l")
            return "".join(seq)

        prefix_clipped = clip_ansi(self._prompt_prefix, max(4, W // 3))
        prefix_w = visible_width(prefix_clipped)
        avail = max(10, W - prefix_w - 1)

        # Clamp cursor index and adjust horizontal scroll window
        self._cursor_idx = max(0, min(len(self._input_buffer), self._cursor_idx))
        if self._cursor_idx < self._view_offset:
            self._view_offset = self._cursor_idx
        elif self._cursor_idx > self._view_offset + avail:
            self._view_offset = self._cursor_idx - avail

        # Ensure multi-column Unicode characters inside the slice fit `avail`
        vis_slice_chars: List[str] = []
        slice_cols = 0
        cursor_col_offset = 0
        for i in range(self._view_offset, len(self._input_buffer)):
            ch = self._input_buffer[i]
            cw = _char_width(ch)
            if slice_cols + cw > avail:
                if i < self._cursor_idx:
                    # Shift view window right so cursor stays visible
                    self._view_offset += 1
                    return self._build_footer_seq()
                break
            if i < self._cursor_idx:
                cursor_col_offset += cw
            vis_slice_chars.append(ch)
            slice_cols += cw

        vis_slice = "".join(vis_slice_chars)
        target_col = 1 + prefix_w + cursor_col_offset
        seq.append(
            f"\033[{p_row};1H\033[2K{prefix_clipped}{vis_slice}"
            f"\033[{p_row};{target_col}H\033[?25h"
        )
        return "".join(seq)

    def _build_cursor_park_seq(self) -> str:
        """Returns sequence to park cursor cleanly in Zone 3 without full separator redraw."""
        p_row = self.prompt_row
        W = self._usable_width

        if self._footer_override is not None:
            clipped = clip_ansi(self._footer_override, W)
            col = min(W + 1, max(1, visible_width(clipped) + 1))
            cur_vis = "\033[?25h" if self._footer_override_cursor else "\033[?25l"
            return f"\033[{p_row};{col}H{cur_vis}"

        if not self._prompt_active:
            return f"\033[{p_row};1H\033[?25l"

        prefix_w = visible_width(clip_ansi(self._prompt_prefix, max(4, W // 3)))
        cursor_cols = sum(
            _char_width(c)
            for c in self._input_buffer[self._view_offset : self._cursor_idx]
        )
        target_col = min(W + 1, 1 + prefix_w + cursor_cols)
        return f"\033[{p_row};{target_col}H\033[?25h"

    # ── Full Redraw (Init, Resize, F5, Exit Modal) ────────────────────────────

    def full_redraw(self) -> None:
        """Clears screen, sets DECSTBM scroll region, and redraws all 3 zones."""
        with self._lock:
            if not self._active or self._modal:
                return

            W = self._usable_width
            b_top = self.body_top
            b_bot = self.body_bottom
            body_height = max(1, b_bot - b_top + 1)

            seq: List[str] = [
                "\033[?25l",               # Hide cursor during composite redraw
                "\033[?6l",                # Ensure Origin Mode (DECOM) is OFF (absolute coords)
                "\033[r",                  # Reset any previous scroll margins
                "\033[2J\033[H",           # Clear full viewport and home cursor
                f"\033[{b_top};{b_bot}r",  # Lock Zone 2 scroll region (DECSTBM)
            ]

            # 1. Zone 1: Header rows 1..5
            for idx in range(HEADER_ROWS):
                raw_row = self._header_cache[idx] if idx < len(self._header_cache) else ""
                clipped = clip_ansi(raw_row, W)
                seq.append(f"\033[{idx + 1};1H\033[2K{clipped}")

            # 2. Zone 2: Replay wrapped tail of body history inside 6..body_bottom
            visual_lines: List[str] = []
            for logical in self._body_history:
                visual_lines.extend(wrap_ansi_line(logical, W))

            tail = visual_lines[-body_height:] if visual_lines else []
            self._body_row = b_top
            self._body_bottom_occupied = False

            for vline in tail:
                if self._body_row < b_bot:
                    seq.append(f"\033[{self._body_row};1H\033[2K{vline}")
                    self._body_row += 1
                else:
                    seq.append(f"\033[{b_bot};1H\033[2K{vline}")
                    self._body_bottom_occupied = True

            # 3. Zone 3: Footer + Cursor Park
            seq.append(self._build_footer_seq())
            self._write_raw("".join(seq))

    # ── Zone 1: Header Rendering ──────────────────────────────────────────────

    def render_header(self, rows: List[str], force: bool = False) -> None:
        """
        Atomically updates Header Rows 1..5 and parks the cursor back in Zone 3.
        Skips terminal I/O completely if clipped rows are identical and `force` is False.
        """
        with self._lock:
            padded_rows = (list(rows) + [""] * HEADER_ROWS)[:HEADER_ROWS]

            if not self._active or self._modal:
                self._header_cache = padded_rows
                return

            if self.refresh_dimensions():
                self._header_cache = padded_rows
                self.full_redraw()
                return

            W = self._usable_width
            clipped_new = [clip_ansi(r, W) for r in padded_rows]
            clipped_old = [clip_ansi(r, W) for r in self._header_cache]
            self._header_cache = padded_rows

            if not force and clipped_new == clipped_old:
                return

            seq: List[str] = ["\033[?25l"]
            for idx, crow in enumerate(clipped_new):
                if force or crow != clipped_old[idx]:
                    seq.append(f"\033[{idx + 1};1H\033[2K{crow}")
            seq.append(self._build_cursor_park_seq())
            self._write_raw("".join(seq))

    def render_header_row(self, row_index_1based: int, row_text: str) -> None:
        """Atomically updates a single Header Row (1..5) and parks the cursor in Zone 3."""
        if not (1 <= row_index_1based <= HEADER_ROWS):
            return
        with self._lock:
            idx = row_index_1based - 1
            self._header_cache[idx] = row_text
            if not self._active or self._modal:
                return
            if self.refresh_dimensions():
                self.full_redraw()
                return

            W = self._usable_width
            clipped = clip_ansi(row_text, W)
            seq = (
                f"\033[?25l"
                f"\033[{row_index_1based};1H\033[2K{clipped}"
                f"{self._build_cursor_park_seq()}"
            )
            self._write_raw(seq)

    # ── Zone 2: Scrollable Body Output ────────────────────────────────────────

    def print_body(self, text: str = "", record_history: bool = True) -> None:
        """
        Prints one or more lines exclusively inside Zone 2 (Rows 6..H-2).
        Scrolls ONLY Zone 2 when full, keeping Zone 1 (Header) and Zone 3 (Footer) untouched.
        """
        with self._lock:
            if text is None:
                text = ""
            logical_lines = str(text).split("\n")

            if record_history:
                for ll in logical_lines:
                    self._body_history.append(ll.rstrip("\r"))

            if not self._active or self._modal:
                self._raw_stdout.write(str(text) + "\n")
                self._raw_stdout.flush()
                return

            if self.refresh_dimensions():
                self.full_redraw()
                return

            W = self._usable_width
            b_bot = self.body_bottom

            visual_chunks: List[str] = []
            for ll in logical_lines:
                visual_chunks.extend(wrap_ansi_line(ll.rstrip("\r"), W))

            seq: List[str] = ["\033[?25l"]
            for chunk in visual_chunks:
                if self._body_row < b_bot:
                    seq.append(f"\033[{self._body_row};1H\033[2K{chunk}")
                    self._body_row += 1
                else:
                    if not self._body_bottom_occupied:
                        seq.append(f"\033[{b_bot};1H\033[2K{chunk}")
                        self._body_bottom_occupied = True
                    else:
                        # Cursor at bottom margin of DECSTBM + LF (\n) scrolls ONLY rows 6..b_bot!
                        seq.append(f"\033[{b_bot};1H\n\033[{b_bot};1H\033[2K{chunk}")

            # Refresh footer & park cursor back in Zone 3
            seq.append(self._build_footer_seq())
            self._write_raw("".join(seq))

    def clear_body(self) -> None:
        """Clears the conversation body history and redraws clean zones."""
        with self._lock:
            self._body_history.clear()
            self._body_row = self.body_top
            self._body_bottom_occupied = False
            if self._active and not self._modal:
                self.full_redraw()

    # ── Zone 3: Input Line & Footer State ─────────────────────────────────────

    def set_prompt(
        self,
        prefix: str,
        buffer: str = "",
        cursor_idx: Optional[int] = None,
        active: bool = True,
    ) -> None:
        """Updates the Zone 3 input prompt state and redraws the footer atomically."""
        with self._lock:
            self._prompt_prefix = prefix
            self._input_buffer = buffer
            self._cursor_idx = len(buffer) if cursor_idx is None else cursor_idx
            if not buffer:
                self._view_offset = 0
            self._prompt_active = active
            if active:
                self._footer_override = None

            if not self._active or self._modal:
                return

            if self.refresh_dimensions():
                self.full_redraw()
                return

            self._write_raw("\033[?25l" + self._build_footer_seq())

    def set_footer_override(
        self, text: Optional[str], show_cursor: bool = False
    ) -> None:
        """
        Temporarily replaces Row H with a status/spinner/confirmation prompt
        (e.g. animated thinking bar or Y/N exit confirmation), or clears it when `text=None`.
        """
        with self._lock:
            self._footer_override = text
            self._footer_override_cursor = show_cursor
            if not self._active or self._modal:
                return
            if self.refresh_dimensions():
                self.full_redraw()
                return
            self._write_raw("\033[?25l" + self._build_footer_seq())

    # ── Modal Screen Management (F1 Help, F2 Models, F3 Soul, F7 ConfigEditor) ─

    def enter_modal(self) -> None:
        """
        Suspends the 3-zone TUI and resets scroll margins so full-screen interactive
        dialogs (F1, F2, F3, F7) can take over the screen cleanly.
        """
        with self._lock:
            self._modal = True
            if self._active:
                self._write_raw("\033[r\033[0m\033[2J\033[H\033[?25h")

    def exit_modal(self) -> None:
        """
        Exits modal mode and restores all 3 zones (including previous chat history!).
        """
        with self._lock:
            enable_native_vt_console()
            self._modal = False
            self.refresh_dimensions()
            if self._active:
                self.full_redraw()


# ── Singleton Accessor ────────────────────────────────────────────────────────

_viewport_instance: Optional[TerminalViewport] = None
_viewport_init_lock = threading.Lock()


def get_viewport() -> TerminalViewport:
    global _viewport_instance
    if _viewport_instance is None:
        with _viewport_init_lock:
            if _viewport_instance is None:
                _viewport_instance = TerminalViewport()
                atexit.register(_viewport_instance.teardown)
    return _viewport_instance
