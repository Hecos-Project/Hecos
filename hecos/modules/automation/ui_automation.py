"""
automation/ui_automation.py
UIAutomation — Windows Accessibility API bridge for Hecos.
Reads structural data (browser tabs, app controls) without needing vision.
Requires: pywinauto, pywin32 (already in service extras)
"""

from hecos.core.logging import logger

_PYWINAUTO_AVAILABLE = None


def _check_pywinauto() -> bool:
    global _PYWINAUTO_AVAILABLE
    if _PYWINAUTO_AVAILABLE is not None:
        return _PYWINAUTO_AVAILABLE
    try:
        import pywinauto  # noqa
        _PYWINAUTO_AVAILABLE = True
    except ImportError:
        _PYWINAUTO_AVAILABLE = False
    return _PYWINAUTO_AVAILABLE


# ─── Browser Tab Reading ────────────────────────────────────────────────────



# Known Chromium-based window class names
_CHROMIUM_CLASSES = {
    "Chrome_WidgetWin_1",   # Chrome, Edge, Opera, Brave, Vivaldi (all Chromium)
}
# Firefox uses a different class
_FIREFOX_CLASSES = {
    "MozillaWindowClass",
    "MozillaDropShadowWindowClass",
}


def _get_browser_windows(desktop) -> list:
    """Return all top-level windows that appear to be a browser."""
    result = []
    for win in desktop.windows():
        try:
            cls = win.class_name()
            title = win.window_text()
            if not title:
                continue
            if cls in _CHROMIUM_CLASSES or cls in _FIREFOX_CLASSES:
                result.append((win, cls))
        except Exception:
            pass
    return result


def _get_chrome_tabs_via_uia() -> list[str]:
    """
    Read tab titles from any supported browser via UI Automation.
    Falls back to the active window title when tab-level UIA is restricted
    (common in recent Chrome versions that throttle accessibility APIs).
    """
    from pywinauto import Desktop
    tabs = []
    desktop = Desktop(backend="uia")

    for win, cls in _get_browser_windows(desktop):
        # Strategy 1: Try to enumerate TabItem controls (works on some Chrome/Edge versions)
        try:
            tab_bar_items = win.descendants(control_type="TabItem")
            for item in tab_bar_items:
                t = item.window_text()
                if t and t not in tabs:
                    tabs.append(t)
        except Exception:
            pass

        # Strategy 2: If no tab items found, use window title (= active tab on that window)
        if not tabs:
            title = win.window_text()
            # Strip browser suffix like " - Google Chrome"
            for suffix in [" - Google Chrome", " - Microsoft Edge", " - Opera", " - Brave"]:
                title = title.replace(suffix, "").strip()
            if title and title not in tabs:
                tabs.append(title)

    return tabs


def get_browser_tabs_tool() -> str:
    """
    Returns a list of all open browser tab titles from Chromium-based browsers.
    Reads directly from the Windows Accessibility tree — no vision required.
    """
    if not _check_pywinauto():
        return (
            "[AUTOMATION] UIAutomation not available. Install pywinauto: pip install pywinauto. "
            "This is required for reading browser tabs without vision."
        )

    try:
        tabs = _get_chrome_tabs_via_uia()
        if not tabs:
            return "[AUTOMATION] No browser tabs found. Make sure Chrome, Edge, or Opera is open."

        tab_list = "\n".join(f"  [{i}] {t}" for i, t in enumerate(tabs))
        return f"[AUTOMATION] Open browser tabs ({len(tabs)}):\n{tab_list}"
    except Exception as e:
        logger.error(f"[AUTOMATION] get_browser_tabs error: {e}")
        return f"[AUTOMATION] Failed to read browser tabs: {e}"


# ─── Focus Browser Tab by Title ─────────────────────────────────────────────


def focus_browser_tab_tool(title_fragment: str) -> str:
    """
    Clicks on a browser tab whose title contains `title_fragment` (case-insensitive).
    Uses the Windows Accessibility tree — no coordinate guessing required.
    """
    if not _check_pywinauto():
        return (
            "[AUTOMATION] UIAutomation not available. Install pywinauto: pip install pywinauto."
        )

    from pywinauto import Desktop
    desktop = Desktop(backend="uia")
    target_lower = title_fragment.lower().strip()

    for win in desktop.windows():
        try:
            if win.class_name() != "Chrome_WidgetWin_1":
                continue

            parent = None
            try:
                tab_bar = win.child_window(control_type="TabItem", found_index=0)
                parent = tab_bar.parent()
            except Exception:
                continue

            for child in parent.children():
                try:
                    if child.element_info.control_type != "TabItem":
                        continue
                    tab_title = child.window_text()
                    if target_lower in tab_title.lower():
                        child.click_input()
                        win.set_focus()
                        return f"[AUTOMATION] Clicked browser tab: '{tab_title}'"
                except Exception:
                    pass
        except Exception:
            pass

    return (
        f"[AUTOMATION] No browser tab found matching '{title_fragment}'. "
        f"Use get_browser_tabs to see the current list."
    )


# ─── Generic Control Inspector ───────────────────────────────────────────────


def read_window_controls_tool(title_fragment: str, max_depth: int = 2) -> str:
    """
    Reads the UI control tree of a window whose title matches `title_fragment`.
    Returns a summary of buttons, edits, and labels — no vision required.
    """
    if not _check_pywinauto():
        return "[AUTOMATION] UIAutomation not available. Install pywinauto."

    from pywinauto import Desktop
    desktop = Desktop(backend="uia")
    target_lower = title_fragment.lower()

    for win in desktop.windows():
        try:
            if target_lower not in win.window_text().lower():
                continue

            results = [f"[AUTOMATION] Window: '{win.window_text()}' — Controls:"]

            def _walk(el, depth):
                if depth > max_depth:
                    return
                try:
                    ct = el.element_info.control_type
                    text = el.window_text()
                    if ct in ("Button", "Edit", "Hyperlink", "MenuItem", "ListItem") and text:
                        results.append(f"{'  ' * depth}[{ct}] {text}")
                    for child in el.children():
                        _walk(child, depth + 1)
                except Exception:
                    pass

            _walk(win, 1)
            return "\n".join(results[:80])  # Cap at 80 lines to avoid token explosion
        except Exception:
            pass

    return f"[AUTOMATION] No window found matching '{title_fragment}'."
