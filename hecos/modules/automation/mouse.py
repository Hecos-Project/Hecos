"""
automation/mouse.py
Mouse control tools: move, click, scroll, drag, position.
All coordinates are in absolute screen pixels.
"""
import time

TAG = "AUTOMATION"

def _gui():
    """Lazy import pyautogui to avoid import-time failures."""
    try:
        import pyautogui
        pyautogui.FAILSAFE = True   # move to top-left corner to abort
        pyautogui.PAUSE = 0.05      # small inter-call delay
        return pyautogui
    except ImportError:
        raise RuntimeError(
            "[AUTOMATION] pyautogui is not installed. "
            "Run: pip install pyautogui"
        )


def get_screen_size_tool() -> str:
    """Returns the screen resolution as WxH."""
    gui = _gui()
    w, h = gui.size()
    return f"[{TAG}] Screen size: {w}x{h} px"


def get_position_tool() -> str:
    """Returns the current mouse cursor position."""
    gui = _gui()
    x, y = gui.position()
    return f"[{TAG}] Cursor position: x={x}, y={y}"


def move_to_tool(x: int, y: int, duration: float = 0.15) -> str:
    """
    Smoothly moves the cursor to absolute coordinates (x, y).
    :param x: Horizontal pixel coordinate.
    :param y: Vertical pixel coordinate.
    :param duration: Movement duration in seconds (0 = instant).
    """
    gui = _gui()
    try:
        gui.moveTo(int(x), int(y), duration=float(duration))
        return f"[{TAG}] Cursor moved to ({x}, {y})."
    except gui.FailSafeException:
        return f"[{TAG}] FailSafe triggered: cursor moved to top-left corner. Operation aborted."
    except Exception as e:
        return f"[{TAG}] move_to error: {e}"


def click_tool(x: int, y: int, button: str = "left", clicks: int = 1, duration: float = 0.1) -> str:
    """
    Clicks the mouse at the given coordinates.
    :param x: Horizontal pixel coordinate.
    :param y: Vertical pixel coordinate.
    :param button: 'left', 'right', or 'middle'.
    :param clicks: Number of clicks (1 = single, 2 = double).
    :param duration: Mouse movement duration before clicking.
    """
    gui = _gui()
    button = button.lower()
    if button not in ("left", "right", "middle"):
        button = "left"
    try:
        gui.click(int(x), int(y), button=button, clicks=int(clicks), duration=float(duration))
        label = "Double-click" if clicks >= 2 else "Click"
        return f"[{TAG}] {label} ({button}) at ({x}, {y})."
    except gui.FailSafeException:
        return f"[{TAG}] FailSafe triggered. Operation aborted."
    except Exception as e:
        return f"[{TAG}] click error: {e}"


def scroll_tool(x: int, y: int, clicks: int = 3) -> str:
    """
    Scrolls the mouse wheel at the given coordinates.
    :param x: Horizontal pixel coordinate.
    :param y: Vertical pixel coordinate.
    :param clicks: Positive = scroll up, negative = scroll down.
    """
    gui = _gui()
    try:
        gui.scroll(int(clicks), int(x), int(y))
        direction = "up" if clicks > 0 else "down"
        return f"[{TAG}] Scrolled {abs(clicks)} clicks {direction} at ({x}, {y})."
    except Exception as e:
        return f"[{TAG}] scroll error: {e}"


def drag_tool(from_x: int, from_y: int, to_x: int, to_y: int, duration: float = 0.4, button: str = "left") -> str:
    """
    Clicks and drags from one position to another.
    :param from_x: Start X.
    :param from_y: Start Y.
    :param to_x: End X.
    :param to_y: End Y.
    :param duration: Duration of the drag in seconds.
    :param button: Mouse button to hold ('left', 'right').
    """
    gui = _gui()
    try:
        gui.moveTo(int(from_x), int(from_y), duration=0.1)
        gui.dragTo(int(to_x), int(to_y), duration=float(duration), button=button)
        return f"[{TAG}] Dragged from ({from_x}, {from_y}) to ({to_x}, {to_y})."
    except Exception as e:
        return f"[{TAG}] drag error: {e}"
