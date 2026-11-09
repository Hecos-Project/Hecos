"""
hecos/ui/ansi.py
ANSI parsing, Unicode wide-character width calculation, safe clipping/wrapping,
and native Win32 VT100 console mode activation.
"""

from __future__ import annotations

import os
import re
import unicodedata
from typing import List

# Matches CSI (\x1b[...X), OSC (\x1b]...BEL or ST), and single-char ESC sequences
ANSI_TOKEN_RE = re.compile(
    r'(\x1b\[[0-?]*[ -/]*[@-~]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b[@-Z\\-_])'
)

HEADER_ROWS = 5
FOOTER_ROWS = 2
MIN_TERM_COLS = 60
MIN_TERM_ROWS = 12


def strip_ansi(text: str) -> str:
    """Removes all ANSI escape sequences from a string."""
    if not text:
        return ""
    return ANSI_TOKEN_RE.sub("", text)


def char_width(ch: str) -> int:
    """Returns terminal column width of a single Unicode character."""
    code = ord(ch)
    if code < 32 or (0x7F <= code < 0xA0):
        return 0
    cat = unicodedata.category(ch)
    if cat in ("Mn", "Me", "Cf"):
        return 0
    # East Asian Wide / Fullwidth characters (including emojis like 🔴, 🚀) take 2 columns.
    # Note: Ambiguous ('A') characters such as box-drawing (─, │, █, ░, ━) are 1 column
    # in Western/UTF-8 Windows Terminal and conhost.
    if unicodedata.east_asian_width(ch) in ("W", "F"):
        return 2
    return 1


def visible_width(text: str) -> int:
    """Calculates visible column width of an ANSI-formatted string."""
    if not text:
        return 0
    plain = strip_ansi(text)
    return sum(char_width(c) for c in plain)


def clip_ansi(text: str, max_cols: int, pad: bool = False) -> str:
    """
    Clips an ANSI string so its visible width never exceeds `max_cols`.
    Preserves color codes up to the cut point and resets attributes cleanly.
    """
    if max_cols <= 0:
        return ""
    if not text:
        return " " * max_cols if pad else ""

    parts = ANSI_TOKEN_RE.split(text)
    out: List[str] = []
    cols = 0
    has_ansi = False
    truncated = False

    for idx, part in enumerate(parts):
        if not part:
            continue
        if idx % 2 == 1:
            # ANSI sequence token
            has_ansi = True
            out.append(part)
        else:
            for ch in part:
                w = char_width(ch)
                if cols + w > max_cols:
                    truncated = True
                    break
                out.append(ch)
                cols += w
            if truncated:
                break

    if has_ansi:
        out.append("\033[0m")

    if pad and cols < max_cols:
        out.append(" " * (max_cols - cols))

    return "".join(out)


def wrap_ansi_line(line: str, max_cols: int) -> List[str]:
    """
    Wraps a single logical line (no embedded \\n) into visual lines of at most `max_cols`
    visible columns, carrying active SGR sequences across line breaks.
    """
    if max_cols <= 0:
        return [""]
    if not line:
        return [""]

    if visible_width(line) <= max_cols:
        return [line]

    parts = ANSI_TOKEN_RE.split(line)
    chunks: List[str] = []
    cur_buf: List[str] = []
    cur_cols = 0
    active_sgr: List[str] = []

    for idx, part in enumerate(parts):
        if not part:
            continue
        if idx % 2 == 1:
            cur_buf.append(part)
            if part.endswith("m"):
                if part in ("\033[0m", "\033[m"):
                    active_sgr.clear()
                else:
                    active_sgr.append(part)
        else:
            for ch in part:
                w = char_width(ch)
                if cur_cols + w > max_cols and cur_cols > 0:
                    if active_sgr:
                        cur_buf.append("\033[0m")
                    chunks.append("".join(cur_buf))
                    cur_buf = list(active_sgr)
                    cur_cols = 0
                cur_buf.append(ch)
                cur_cols += w

    if cur_buf or not chunks:
        chunks.append("".join(cur_buf))

    return chunks


def enable_native_vt_console() -> bool:
    """
    Enables UTF-8 codepage (65001) and native Win32 Virtual Terminal Processing
    in-process without spawning `chcp` subshells (which reset console flags).
    """
    if os.name != "nt":
        return True

    try:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleOutputCP(65001)
        kernel32.SetConsoleCP(65001)

        ENABLE_PROCESSED_OUTPUT = 0x0001
        ENABLE_WRAP_AT_EOL_OUTPUT = 0x0002
        ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        DISABLE_NEWLINE_AUTO_RETURN = 0x0008

        ok = False
        for std_handle_id in (-11, -12):  # STD_OUTPUT_HANDLE, STD_ERROR_HANDLE
            handle = kernel32.GetStdHandle(std_handle_id)
            if handle and handle != -1:
                mode = wintypes.DWORD()
                if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                    new_mode = (
                        mode.value
                        | ENABLE_PROCESSED_OUTPUT
                        | ENABLE_WRAP_AT_EOL_OUTPUT
                        | ENABLE_VIRTUAL_TERMINAL_PROCESSING
                    ) & ~DISABLE_NEWLINE_AUTO_RETURN
                    if kernel32.SetConsoleMode(handle, new_mode):
                        ok = True
        return ok
    except Exception:
        return False

