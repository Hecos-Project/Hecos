"""
automation/windows.py
Window management tools: list, focus, minimize, maximize.
Uses pygetwindow on Windows/macOS.
"""
import sys

TAG = "AUTOMATION"


def _gw():
    try:
        import pygetwindow as gw
        return gw
    except ImportError:
        raise RuntimeError(
            "[AUTOMATION] pygetwindow is not installed. Run: pip install pygetwindow"
        )


def list_windows_tool() -> str:
    """
    Returns a list of all currently visible window titles.
    Use this to find the exact title before calling focus_window.
    """
    try:
        gw = _gw()
        titles = [t for t in gw.getAllTitles() if t.strip()]
        if not titles:
            return "[AUTOMATION] No visible windows found."
        lines = "\n".join(f"  - {t}" for t in sorted(titles))
        return f"[AUTOMATION] Open windows ({len(titles)}):\n{lines}"
    except Exception as e:
        return f"[AUTOMATION] list_windows error: {e}"


def focus_window_tool(title: str) -> str:
    """
    Brings the window whose title contains the given string to the foreground.
    Case-insensitive partial match. Use list_windows first to get exact titles.
    :param title: Partial or full window title (e.g. 'Notepad', 'Chrome').
    """
    try:
        gw = _gw()
        matches = [w for w in gw.getAllWindows() if title.lower() in w.title.lower()]
        if not matches:
            return f"[AUTOMATION] No window found matching: '{title}'. Use list_windows to see available windows."
        win = matches[0]
        win.restore()   
        win.activate()
        return f"[AUTOMATION] Focused window: '{win.title}'"
    except Exception as e:
        return f"[AUTOMATION] focus_window error: {e}"


def minimize_window_tool(title: str) -> str:
    """
    Minimizes the window whose title contains the given string.
    :param title: Partial or full window title.
    """
    try:
        gw = _gw()
        matches = [w for w in gw.getAllWindows() if title.lower() in w.title.lower()]
        if not matches:
            return f"[AUTOMATION] No window found matching: '{title}'."
        matches[0].minimize()
        return f"[AUTOMATION] Minimized: '{matches[0].title}'"
    except Exception as e:
        return f"[AUTOMATION] minimize_window error: {e}"


def maximize_window_tool(title: str) -> str:
    """
    Maximizes the window whose title contains the given string.
    :param title: Partial or full window title.
    """
    try:
        gw = _gw()
        matches = [w for w in gw.getAllWindows() if title.lower() in w.title.lower()]
        if not matches:
            return f"[AUTOMATION] No window found matching: '{title}'."
        matches[0].maximize()
        return f"[AUTOMATION] Maximized: '{matches[0].title}'"
    except Exception as e:
        return f"[AUTOMATION] maximize_window error: {e}"
