"""
automation/keyboard.py
Keyboard control tools: type text, press keys, hotkeys.
"""

TAG = "AUTOMATION"

# Human-readable key aliases for documentation clarity
VALID_SPECIAL_KEYS = [
    "enter", "return", "esc", "escape", "tab", "backspace", "delete", "del",
    "space", "up", "down", "left", "right",
    "home", "end", "pageup", "pagedown",
    "f1","f2","f3","f4","f5","f6","f7","f8","f9","f10","f11","f12",
    "ctrl", "alt", "shift", "win", "command", "option",
    "capslock", "numlock", "scrolllock", "printscreen",
    "insert", "pause", "volumeup", "volumedown", "volumemute",
]


def _gui():
    try:
        import pyautogui
        return pyautogui
    except ImportError:
        raise RuntimeError(
            "[AUTOMATION] pyautogui is not installed. Run: pip install pyautogui"
        )


def type_text_tool(text: str, interval: float = 0.02) -> str:
    """
    Simulates keyboard typing of the given text, character by character.
    :param text: The string to type. Supports Unicode.
    :param interval: Pause between keystrokes in seconds (default: 0.02).
    """
    gui = _gui()
    try:
        gui.typewrite(text, interval=float(interval))
        preview = text[:40] + ("..." if len(text) > 40 else "")
        return f"[{TAG}] Typed: \"{preview}\""
    except Exception as e:
        # Fallback for unicode chars that typewrite can't handle
        try:
            import pyperclip
            pyperclip.copy(text)
            gui.hotkey("ctrl", "v")
            return f"[{TAG}] Typed via clipboard paste (Unicode fallback): \"{text[:40]}\""
        except Exception:
            return f"[{TAG}] type_text error: {e}"


def press_key_tool(key: str) -> str:
    """
    Presses and releases a single keyboard key.
    :param key: Key name (e.g. 'enter', 'esc', 'f5', 'tab', 'delete').
    """
    gui = _gui()
    key = key.lower().strip()
    try:
        gui.press(key)
        return f"[{TAG}] Key pressed: '{key}'"
    except Exception as e:
        return f"[{TAG}] press_key error: {e}"


def hotkey_tool(keys: list) -> str:
    """
    Presses a keyboard shortcut (chord) by holding all keys simultaneously.
    :param keys: List of key names in order (e.g. ['ctrl', 'c'] or ['ctrl', 'shift', 'esc']).
    """
    gui = _gui()
    if isinstance(keys, str):
        # Handle case where LLM sends a string like "ctrl+c"
        keys = [k.strip() for k in keys.replace("+", ",").split(",")]
    try:
        gui.hotkey(*[k.lower().strip() for k in keys])
        return f"[{TAG}] Hotkey executed: {' + '.join(keys)}"
    except Exception as e:
        return f"[{TAG}] hotkey error: {e}"


def write_line_tool(text: str) -> str:
    """
    Types the given text and immediately presses Enter.
    Useful for filling form fields or running terminal commands.
    :param text: The text to type before pressing Enter.
    """
    gui = _gui()
    try:
        gui.typewrite(text, interval=0.02)
        gui.press("enter")
        preview = text[:60] + ("..." if len(text) > 60 else "")
        return f"[{TAG}] Typed and confirmed: \"{preview}\""
    except Exception as e:
        return f"[{TAG}] write_line error: {e}"
