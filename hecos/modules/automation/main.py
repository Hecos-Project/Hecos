"""
automation/main.py
AutomationTools — PC Control Module for Hecos.
Wraps mouse, keyboard, and window management into AI-callable tools.
"""

try:
    from hecos.core.i18n import translator
    from hecos.app.config import ConfigManager
except ImportError:
    class DummyTranslator:
        def t(self, key, **kwargs): return key
    translator = DummyTranslator()
    class DummyConfigMgr:
        def __init__(self): self.config = {}
        def get_plugin_config(self, tag, key, default): return default
    def ConfigManager(): return DummyConfigMgr()

from .mouse import (
    get_screen_size_tool, get_position_tool, move_to_tool,
    click_tool, scroll_tool, drag_tool
)
from .keyboard import (
    type_text_tool, press_key_tool, hotkey_tool, write_line_tool
)
from .windows import (
    list_windows_tool, focus_window_tool,
    minimize_window_tool, maximize_window_tool
)
from .ui_automation import (
    get_browser_tabs_tool, focus_browser_tab_tool, read_window_controls_tool
)


class AutomationTools:
    """
    Hecos PC Automation — Full control of mouse, keyboard, and windows.
    Combine with WEBCAM.desktop_screenshot() to implement a full
    'see screen → act on it' loop.
    """

    def __init__(self):
        self.tag = "AUTOMATION"
        self.desc = (
            "PC Automation: control the mouse, keyboard, and application windows. "
            "Use with desktop_screenshot for a full see-and-act loop."
        )
        self.routing_instructions = (
            "VISION/AUTOMATION SYNERGY: You DO have 'eyes'! You can interact with the user's screen. "
            "When asked to click on something or read the screen, FIRST call WEBCAM__desktop_screenshot. "
            "The system will return the image to your context. "
            "THEN analyze the image to find the exact (x, y) coordinates. "
            "FINALLY, call AUTOMATION__move_to or AUTOMATION__click with those coordinates."
        )
        self.status = "ONLINE"

        self.config_schema = {
            "enabled": {
                "type": "bool",
                "default": True,
                "description": "Master switch. Disable to prevent any PC control action."
            },
            "move_duration": {
                "type": "float",
                "default": 0.15,
                "description": "Default mouse movement duration in seconds (0 = instant)."
            },
            "type_interval": {
                "type": "float",
                "default": 0.02,
                "description": "Delay between keystrokes in seconds."
            },
            "allow_window_control": {
                "type": "bool",
                "default": True,
                "description": "Enable pygetwindow-based window management."
            }
        }

    def _check_enabled(self):
        try:
            cfg = ConfigManager()
            return cfg.get_plugin_config(self.tag, "enabled", True)
        except Exception:
            return True

    # ─── Mouse ─────────────────────────────────────────────────────────────────

    def get_screen_size(self) -> str:
        """Returns the screen resolution (width x height in pixels)."""
        if not self._check_enabled(): return "[AUTOMATION] Disabled in config."
        return get_screen_size_tool()

    def get_mouse_position(self) -> str:
        """Returns the current mouse cursor coordinates (x, y)."""
        if not self._check_enabled(): return "[AUTOMATION] Disabled in config."
        return get_position_tool()

    def move_to(self, x: int, y: int, duration: float = 0.15) -> str:
        """
        Moves the mouse cursor to the specified screen coordinates.
        :param x: Horizontal pixel (0 = left edge).
        :param y: Vertical pixel (0 = top edge).
        :param duration: Seconds for the movement animation (0 = instant).
        """
        if not self._check_enabled(): return "[AUTOMATION] Disabled in config."
        try:
            cfg = ConfigManager()
            default_dur = cfg.get_plugin_config(self.tag, "move_duration", 0.15)
        except Exception:
            default_dur = 0.15
        return move_to_tool(x, y, duration if duration != 0.15 else default_dur)

    def click(self, x: int, y: int, button: str = "left", clicks: int = 1) -> str:
        """
        Clicks the mouse at the given screen coordinates.
        :param x: Horizontal pixel coordinate.
        :param y: Vertical pixel coordinate.
        :param button: 'left' (default), 'right', or 'middle'.
        :param clicks: 1 = single click, 2 = double click.
        """
        if not self._check_enabled(): return "[AUTOMATION] Disabled in config."
        return click_tool(x, y, button=button, clicks=clicks)

    def scroll(self, x: int, y: int, clicks: int = 3) -> str:
        """
        Scrolls the mouse wheel at the specified position.
        :param x: Horizontal coordinate.
        :param y: Vertical coordinate.
        :param clicks: Positive = scroll up, negative = scroll down.
        """
        if not self._check_enabled(): return "[AUTOMATION] Disabled in config."
        return scroll_tool(x, y, clicks)

    def drag(self, from_x: int, from_y: int, to_x: int, to_y: int, duration: float = 0.4) -> str:
        """
        Clicks and drags from one position to another (e.g. moving a file, selecting text).
        :param from_x: Start X coordinate.
        :param from_y: Start Y coordinate.
        :param to_x: End X coordinate.
        :param to_y: End Y coordinate.
        :param duration: Duration of the drag animation in seconds.
        """
        if not self._check_enabled(): return "[AUTOMATION] Disabled in config."
        return drag_tool(from_x, from_y, to_x, to_y, duration)

    def click_text(self, text: str, instance: int = 0, button: str = "left", clicks: int = 1) -> str:
        """
        Locates text on the screen via OCR and clicks it.
        :param text: The exact word or short phrase to find.
        :param instance: If there are multiple matches, which one to click (0 = first, 1 = second).
        :param button: 'left' (default), 'right', or 'middle'.
        :param clicks: 1 = single click, 2 = double click.
        """
        if not self._check_enabled(): return "[AUTOMATION] Disabled in config."
        
        try:
            from .ocr import find_text_on_screen, TesseractNotFoundError
            coords = find_text_on_screen(text, instance)
        except TesseractNotFoundError as e:
            return f"[AUTOMATION] {e}"
        except Exception as e:
            return f"[AUTOMATION] OCR scanning failed: {e}"
            
        if not coords:
            return f"[AUTOMATION] Could not find the text '{text}' on screen. Try slightly different wording."
            
        x, y = coords
        try:
            cfg = ConfigManager()
            dur = cfg.get_plugin_config(self.tag, "move_duration", 0.15)
        except Exception:
            dur = 0.15
            
        move_to_tool(x, y, dur)
        res = click_tool(x, y, button=button, clicks=clicks)
        return f"[AUTOMATION] Found '{text}' at ({x}, {y}). {res}"

    # ─── Keyboard ──────────────────────────────────────────────────────────────

    def type_text(self, text: str, interval: float = 0.02) -> str:
        """
        Types the given text as simulated keystrokes.
        :param text: The text to type. Use write_line to also press Enter.
        :param interval: Delay between keystrokes in seconds.
        """
        if not self._check_enabled(): return "[AUTOMATION] Disabled in config."
        return type_text_tool(text, interval)

    def press_key(self, key: str) -> str:
        """
        Presses and releases a single key.
        :param key: Key name, e.g. 'enter', 'esc', 'tab', 'f5', 'delete', 'space'.
        """
        if not self._check_enabled(): return "[AUTOMATION] Disabled in config."
        return press_key_tool(key)

    def hotkey(self, keys: list) -> str:
        """
        Executes a keyboard shortcut by holding multiple keys simultaneously.
        :param keys: List of keys in order, e.g. ['ctrl', 'c'] or ['ctrl', 'shift', 'esc'].
        """
        if not self._check_enabled(): return "[AUTOMATION] Disabled in config."
        return hotkey_tool(keys)

    def type_and_enter(self, text: str) -> str:
        """
        Types the given text and immediately presses Enter.
        Ideal for submitting forms, running terminal commands, or confirming dialogs.
        :param text: The text to type.
        """
        if not self._check_enabled(): return "[AUTOMATION] Disabled in config."
        return write_line_tool(text)

    # ─── Windows ───────────────────────────────────────────────────────────────

    def list_windows(self) -> str:
        """
        Returns a list of all currently visible window titles.
        Use this BEFORE focus_window to find the exact window title.
        """
        if not self._check_enabled(): return "[AUTOMATION] Disabled in config."
        return list_windows_tool()

    def focus_window(self, title: str) -> str:
        """
        Brings a window to the foreground by partial title match.
        :param title: Part of the window title (case-insensitive), e.g. 'Notepad', 'Chrome'.
        """
        if not self._check_enabled(): return "[AUTOMATION] Disabled in config."
        return focus_window_tool(title)

    def minimize_window(self, title: str) -> str:
        """
        Minimizes a window by partial title match.
        :param title: Part of the window title (case-insensitive).
        """
        if not self._check_enabled(): return "[AUTOMATION] Disabled in config."
        return minimize_window_tool(title)

    def maximize_window(self, title: str) -> str:
        """
        Maximizes a window by partial title match.
        :param title: Part of the window title (case-insensitive).
        """
        if not self._check_enabled(): return "[AUTOMATION] Disabled in config."
        return maximize_window_tool(title)

    # ─── UIAutomation (Accessibility API) ────────────────────────────────────

    def get_browser_tabs(self) -> str:
        """
        Returns the titles of all currently open tabs in Chrome, Edge, Opera, or Brave.
        Uses the Windows Accessibility API — no screenshot needed.
        Call this before focus_browser_tab to find the right tab name.
        """
        if not self._check_enabled(): return "[AUTOMATION] Disabled in config."
        return get_browser_tabs_tool()

    def focus_browser_tab(self, title_fragment: str) -> str:
        """
        Clicks on a browser tab whose title contains the given text fragment (case-insensitive).
        Uses the Windows Accessibility API — no coordinate guessing.
        :param title_fragment: Part of the tab title, e.g. 'YouTube' or 'Wikipedia'.
        """
        if not self._check_enabled(): return "[AUTOMATION] Disabled in config."
        return focus_browser_tab_tool(title_fragment)

    def read_window_controls(self, title_fragment: str) -> str:
        """
        Reads the UI control tree (buttons, inputs, links) of an application window.
        Useful for understanding the structure of a GUI before interacting with it.
        :param title_fragment: Part of the window title to target.
        """
        if not self._check_enabled(): return "[AUTOMATION] Disabled in config."
        return read_window_controls_tool(title_fragment)


# ── Singleton ──────────────────────────────────────────────────────────────────
tools = AutomationTools()


def info():
    return {"tag": tools.tag, "desc": tools.desc}


def status():
    return tools.status


def get_plugin():
    return tools
