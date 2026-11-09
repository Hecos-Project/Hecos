"""
hecos/ui/terminal_input.py
Handles Unicode line-editing inside Zone 3 (Footer) and Win32 console keyboard events.
Supports full Italian/Unicode input (àèéìòù, AltGr @#[], Alt+Numpad ~`), cursor navigation
(Left/Right/Home/End/Delete/Backspace), horizontal scrolling, paste batching, Up/Down history,
F1-F9 shortcuts, and instant window-resize detection.
"""
import sys
import os
import json
import threading
import logging

from colorama import Fore, Style
from hecos.ui.viewport import get_viewport

_cli_history = []
_cli_history_idx = -1
_cli_history_draft = ""
_cli_history_loaded = False

# Prompt & line-editor state
_prompt_active = False
_active_prompt_prefix = ""
_active_input_buffer = ""
_cursor_pos = 0
_current_prompt_len = 0
_hint_timer = None


# ── Win32 Console Input Structures (Zero ambiguity for Italian UTF-16 chars) ──

if os.name == "nt":
    import ctypes
    from ctypes import wintypes
    import msvcrt

    _kernel32 = ctypes.windll.kernel32
    _STD_INPUT_HANDLE = -10
    _KEY_EVENT = 0x0001
    _WINDOW_BUFFER_SIZE_EVENT = 0x0004

    class _UCHAR_UNION(ctypes.Union):
        _fields_ = [("UnicodeChar", wintypes.WCHAR), ("AsciiChar", ctypes.c_char)]

    class _KEY_EVENT_RECORD(ctypes.Structure):
        _fields_ = [
            ("bKeyDown", wintypes.BOOL),
            ("wRepeatCount", wintypes.WORD),
            ("wVirtualKeyCode", wintypes.WORD),
            ("wVirtualScanCode", wintypes.WORD),
            ("uChar", _UCHAR_UNION),
            ("dwControlKeyState", wintypes.DWORD),
        ]

    class _EVENT_UNION(ctypes.Union):
        _fields_ = [
            ("KeyEvent", _KEY_EVENT_RECORD),
            ("_pad", ctypes.c_byte * 16),
        ]

    class _INPUT_RECORD(ctypes.Structure):
        _fields_ = [
            ("EventType", wintypes.WORD),
            ("Event", _EVENT_UNION),
        ]

    _VK_F_KEYS = {
        0x70: "F1",
        0x71: "F2",
        0x72: "F3",
        0x73: "F4",
        0x74: "F5",
        0x75: "F6",
        0x76: "F7",
        0x77: "F8",
        0x78: "F9",
    }


def set_active_prompt(prefix: str, buf: str = ""):
    """Registers the current prompt state and renders Zone 3 via TerminalViewport."""
    global _prompt_active, _active_prompt_prefix, _active_input_buffer, _cursor_pos
    _prompt_active = bool(prefix)
    _active_prompt_prefix = prefix
    _active_input_buffer = buf
    _cursor_pos = len(buf)
    get_viewport().set_prompt(prefix, buf, cursor_idx=_cursor_pos, active=_prompt_active)


def print_scrolling(text):
    """Safely prints a message inside Zone 2 (Body) without touching Header or Prompt."""
    get_viewport().print_body(text)


def write_hecos(text):
    """Prints Hecos's response cleanly inside Zone 2 (Body) with visual spacing."""
    from hecos.core.processing import filtri
    text = filtri.clean_for_video(text)
    prefix = f"{Fore.CYAN}HECOS:{Style.RESET_ALL} "
    vp = get_viewport()
    vp.print_body(prefix + text)
    vp.print_body("")


def _ensure_history_loaded():
    global _cli_history, _cli_history_loaded
    if _cli_history_loaded:
        return
    _cli_history_loaded = True
    _ih_log = logging.getLogger("hecos.input_history")
    try:
        _cfg_mgr = getattr(sys, "hecos_config_manager", None)
        if _cfg_mgr:
            _ih_cfg = _cfg_mgr.config.get("input_history", {})
            if _ih_cfg.get("enabled", True) and _ih_cfg.get("persist", True):
                _hist_path = os.path.join(_cfg_mgr.data_dir, "cli_history.json")
                if os.path.exists(_hist_path):
                    with open(_hist_path, "r", encoding="utf-8") as _f:
                        _cli_history = json.load(_f)
                    _ih_log.info(f"[InputHistory:CLI] Loaded {len(_cli_history)} entries from disk.")
                else:
                    _ih_log.info("[InputHistory:CLI] No persisted history found on disk.")
        else:
            _ih_log.info("[InputHistory:CLI] hecos_config_manager not available yet, using RAM only.")
    except Exception as _e:
        _ih_log.warning(f"[InputHistory:CLI] Failed to load from disk: {_e}")


def _navigate_history(direction: str, prefix: str, current_input: str) -> str:
    """Handles Up/Down arrow history navigation."""
    global _cli_history_idx, _cli_history_draft, _cursor_pos, _hint_timer
    _ih_log = logging.getLogger("hecos.input_history")
    _ensure_history_loaded()
    vp = get_viewport()

    if not _cli_history:
        _ih_log.info("[InputHistory:CLI] ArrowUp pressed but history is empty.")
        _msg = "\033[90m [No input history yet — start typing and press Enter]\033[0m"
        vp.set_footer_override(_msg, show_cursor=False)
        if _hint_timer:
            _hint_timer.cancel()

        def _restore():
            if _prompt_active:
                vp.set_prompt(_active_prompt_prefix, _active_input_buffer, cursor_idx=_cursor_pos, active=True)

        _hint_timer = threading.Timer(0.9, _restore)
        _hint_timer.daemon = True
        _hint_timer.start()
        return current_input

    if _cli_history_idx == -1:
        _cli_history_draft = current_input
        _cli_history_idx = len(_cli_history)

    if direction == "UP":
        if _cli_history_idx > 0:
            _cli_history_idx -= 1
    else:
        if _cli_history_idx < len(_cli_history):
            _cli_history_idx += 1

    if _cli_history_idx >= len(_cli_history):
        new_input = _cli_history_draft
        _cli_history_idx = -1
    else:
        new_input = _cli_history[_cli_history_idx]

    if new_input != current_input:
        _cursor_pos = len(new_input)
        vp.set_prompt(prefix, new_input, cursor_idx=_cursor_pos, active=True)
        _ih_log.debug(f"[InputHistory:CLI] Navigated to: {new_input!r}")
    return new_input


def _read_win32_event():
    """
    Reads the next pending Win32 console event non-blockingly.
    Returns one of:
      - None (no relevant event pending)
      - ("RESIZE", None)
      - ("F1".."F9" | "UP" | "DOWN" | "LEFT" | "RIGHT" | "HOME" | "END" | "DELETE" | "BACKSPACE" | "ENTER" | "ESC", None)
      - ("TEXT", str_of_one_or_more_unicode_chars)
    """
    h_in = _kernel32.GetStdHandle(_STD_INPUT_HANDLE)
    if not h_in or h_in == -1:
        return None

    pending = wintypes.DWORD(0)
    if not _kernel32.GetNumberOfConsoleInputEvents(h_in, ctypes.byref(pending)) or pending.value == 0:
        return None

    rec = _INPUT_RECORD()
    read_count = wintypes.DWORD(0)

    while pending.value > 0:
        if not _kernel32.ReadConsoleInputW(h_in, ctypes.byref(rec), 1, ctypes.byref(read_count)) or read_count.value == 0:
            return None

        if rec.EventType == _WINDOW_BUFFER_SIZE_EVENT:
            return ("RESIZE", None)

        if rec.EventType == _KEY_EVENT:
            ke = rec.Event.KeyEvent
            vk = ke.wVirtualKeyCode
            uch = ke.uChar.UnicodeChar or ""
            uord = ord(uch) if uch else 0

            # Support Alt+Numpad character release (e.g. Alt+126 -> '~' on Italian keyboards)
            if not ke.bKeyDown:
                if vk == 0x12 and uord >= 32:  # VK_MENU release with synthesized Unicode char
                    return ("TEXT", uch)
                _kernel32.GetNumberOfConsoleInputEvents(h_in, ctypes.byref(pending))
                continue

            # Function keys F1-F9
            if vk in _VK_F_KEYS:
                return (_VK_F_KEYS[vk], None)

            # Navigation & control keys
            if vk == 0x26:
                return ("UP", None)
            if vk == 0x28:
                return ("DOWN", None)
            if vk == 0x25:
                return ("LEFT", None)
            if vk == 0x27:
                return ("RIGHT", None)
            if vk == 0x24:
                return ("HOME", None)
            if vk == 0x23:
                return ("END", None)
            if vk == 0x2E:
                return ("DELETE", None)
            if vk == 0x1B:
                return ("ESC", None)
            if vk == 0x0D:
                return ("ENTER", None)
            if vk == 0x08:
                return ("BACKSPACE", None)

            # Printable Unicode character (including Italian accented àèéìòù, € and AltGr symbols)
            if uord >= 32 and uord != 0x7F:
                chars = [uch * max(1, ke.wRepeatCount)]
                # Batch-drain any immediately queued printable chars (fast paste support)
                while True:
                    rem = wintypes.DWORD(0)
                    if not _kernel32.GetNumberOfConsoleInputEvents(h_in, ctypes.byref(rem)) or rem.value == 0:
                        break
                    peek_rec = _INPUT_RECORD()
                    peek_cnt = wintypes.DWORD(0)
                    if not _kernel32.PeekConsoleInputW(h_in, ctypes.byref(peek_rec), 1, ctypes.byref(peek_cnt)) or peek_cnt.value == 0:
                        break
                    if peek_rec.EventType != _KEY_EVENT:
                        break
                    pke = peek_rec.Event.KeyEvent
                    puch = pke.uChar.UnicodeChar or ""
                    puord = ord(puch) if puch else 0
                    if not pke.bKeyDown:
                        # Consume key-up between pasted chars
                        if pke.wVirtualKeyCode != 0x12 or puord < 32:
                            _kernel32.ReadConsoleInputW(h_in, ctypes.byref(peek_rec), 1, ctypes.byref(peek_cnt))
                            continue
                    if pke.bKeyDown and puord >= 32 and puord != 0x7F and pke.wVirtualKeyCode not in _VK_F_KEYS:
                        _kernel32.ReadConsoleInputW(h_in, ctypes.byref(peek_rec), 1, ctypes.byref(peek_cnt))
                        chars.append(puch * max(1, pke.wRepeatCount))
                        continue
                    break
                return ("TEXT", "".join(chars))

        _kernel32.GetNumberOfConsoleInputEvents(h_in, ctypes.byref(pending))

    return None


def read_keyboard_input(prefix, current_input):
    """
    Reads keyboard events non-blockingly and updates the Zone 3 line editor.
    Returns: (ActionType, NewInputBuffer)
    """
    global _current_prompt_len, _active_input_buffer, _active_prompt_prefix, _cursor_pos, _prompt_active

    # Sync external buffer resets (e.g. after command execution)
    if current_input != _active_input_buffer:
        _active_input_buffer = current_input
        _cursor_pos = min(_cursor_pos, len(current_input))
        if not current_input:
            _cursor_pos = 0

    _active_prompt_prefix = prefix
    _current_prompt_len = len(prefix) + len(current_input)

    if os.name != "nt":
        return None, current_input

    vp = get_viewport()
    ev = _read_win32_event()
    if ev is None:
        return None, current_input

    kind, payload = ev

    if kind == "RESIZE":
        vp.check_resize()
        return None, current_input

    if kind in ("F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9"):
        return kind, current_input

    if kind in ("UP", "DOWN"):
        new_buf = _navigate_history(kind, prefix, current_input)
        _active_input_buffer = new_buf
        return None, new_buf

    if kind == "LEFT":
        if _cursor_pos > 0:
            _cursor_pos -= 1
            vp.set_prompt(prefix, current_input, cursor_idx=_cursor_pos, active=True)
        return None, current_input

    if kind == "RIGHT":
        if _cursor_pos < len(current_input):
            _cursor_pos += 1
            vp.set_prompt(prefix, current_input, cursor_idx=_cursor_pos, active=True)
        return None, current_input

    if kind == "HOME":
        if _cursor_pos != 0:
            _cursor_pos = 0
            vp.set_prompt(prefix, current_input, cursor_idx=_cursor_pos, active=True)
        return None, current_input

    if kind == "END":
        if _cursor_pos != len(current_input):
            _cursor_pos = len(current_input)
            vp.set_prompt(prefix, current_input, cursor_idx=_cursor_pos, active=True)
        return None, current_input

    if kind == "BACKSPACE":
        if _cursor_pos > 0:
            current_input = current_input[: _cursor_pos - 1] + current_input[_cursor_pos:]
            _cursor_pos -= 1
            _active_input_buffer = current_input
            vp.set_prompt(prefix, current_input, cursor_idx=_cursor_pos, active=True)
        return "CHAR", current_input

    if kind == "DELETE":
        if _cursor_pos < len(current_input):
            current_input = current_input[:_cursor_pos] + current_input[_cursor_pos + 1 :]
            _active_input_buffer = current_input
            vp.set_prompt(prefix, current_input, cursor_idx=_cursor_pos, active=True)
        return "CHAR", current_input

    if kind == "ESC":
        if current_input:
            _active_input_buffer = ""
            _cursor_pos = 0
            vp.set_prompt(prefix, "", cursor_idx=0, active=True)
            return "CLEAR", ""
        return "ESC", current_input

    if kind == "ENTER":
        _cursor_pos = 0
        return "ENTER", current_input

    if kind == "TEXT" and payload:
        # Strip accidental newlines if multi-line text was pasted; submit up to first newline or join spaces
        clean_text = payload.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
        current_input = (
            current_input[:_cursor_pos] + clean_text + current_input[_cursor_pos:]
        )
        _cursor_pos += len(clean_text)
        _active_input_buffer = current_input
        vp.set_prompt(prefix, current_input, cursor_idx=_cursor_pos, active=True)
        return "CHAR", current_input

    return None, current_input


def push_cli_history(text):
    """Pushes a new input command into the CLI history buffer."""
    global _cli_history, _cli_history_idx, _cli_history_loaded
    _log = logging.getLogger("hecos.input_history")
    _ensure_history_loaded()
    try:
        cfg_mgr = getattr(sys, "hecos_config_manager", None)
        cfg = cfg_mgr.config.get("input_history", {}) if cfg_mgr else {}

        if not cfg.get("enabled", True):
            _log.debug("[InputHistory:CLI] push_cli_history: disabled, skipping.")
            return

        deduplicate = cfg.get("deduplicate", True)
        if deduplicate and _cli_history and _cli_history[-1] == text:
            _log.debug("[InputHistory:CLI] push_cli_history: deduplicate match, skipping.")
            _cli_history_idx = -1
            return

        _cli_history.append(text)
        max_entries = cfg.get("max_entries", 5)
        if len(_cli_history) > max_entries:
            _cli_history = _cli_history[-max_entries:]
        _cli_history_idx = -1
        _log.info(f"[InputHistory:CLI] Saved: {text!r} | Total: {len(_cli_history)}")

        if cfg.get("persist", True) and cfg_mgr:
            try:
                hist_path = os.path.join(cfg_mgr.data_dir, "cli_history.json")
                with open(hist_path, "w", encoding="utf-8") as f:
                    json.dump(_cli_history, f)
                _log.debug(f"[InputHistory:CLI] Persisted to {hist_path}")
            except Exception as _pe:
                _log.warning(f"[InputHistory:CLI] Persist error: {_pe}")
    except Exception as _e:
        _log.warning(f"[InputHistory:CLI] push_cli_history error: {_e}")
