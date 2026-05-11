"""
browser/interactor.py
Page Interaction Layer — navigation, clicks, typing, JavaScript, screenshots.
"""

import os
import time
from hecos.core.logging import logger
from . import engine
from . import reader


def navigate(url: str) -> str:
    """Go to a URL. Ensures browser is running."""
    page = engine.get_page()
    if page is None:
        return engine._INSTALL_MSG
    try:
        if not url.startswith(("http://", "https://", "file://", "about:")):
            url = "https://" + url
            
        # Protect the Native Webui from being overwritten via CDP
        if "localhost:7070" in page.url or "Hecos" in page.title():
            page = engine.new_tab(url)
            return f"[BROWSER] Opened new tab to: {page.url} — Title: {page.title()}"
            
        page.goto(url, wait_until="domcontentloaded")
        return f"[BROWSER] Navigated to: {page.url} — Title: {page.title()}"
    except Exception as e:
        return f"[BROWSER] Navigation error: {e}"


def click_element(text_or_selector: str) -> str:
    """
    Click an element by its visible text, aria-label, or CSS selector.
    Falls back through each strategy.
    """
    page = engine.get_page()
    if page is None:
        return engine._INSTALL_MSG
    try:
        # Strategy 1: semantic find (aria/text/placeholder)
        loc = reader.find_element(text_or_selector)
        if loc:
            loc.click()
            return f"[BROWSER] Clicked element: '{text_or_selector}'"
        
        # Strategy 2: raw CSS/XPath selector
        try:
            page.click(text_or_selector, timeout=3000)
            return f"[BROWSER] Clicked selector: '{text_or_selector}'"
        except Exception:
            pass
        
        return (
            f"[BROWSER] Could not find element '{text_or_selector}'. "
            "Try get_page_text or get_inputs to identify available elements."
        )
    except Exception as e:
        return f"[BROWSER] click_element error: {e}"


def type_in_field(label_or_selector: str, text: str, press_enter: bool = False) -> str:
    """
    Find an input field by label/placeholder/aria and type text into it.
    Set press_enter=True to submit after typing.
    """
    page = engine.get_page()
    if page is None:
        return engine._INSTALL_MSG
    try:
        # First pass: look specifically for true text inputs or textareas using CSS
        try:
            loc = page.locator(f'input[placeholder*="{label_or_selector}" i], input[aria-label*="{label_or_selector}" i], input[name*="{label_or_selector}" i], textarea[placeholder*="{label_or_selector}" i], #{label_or_selector}').first
            if loc.count() > 0 and loc.is_visible():
                loc.fill(text, timeout=2000)
                if press_enter:
                    loc.press("Enter")
                    try: page.wait_for_load_state("domcontentloaded", timeout=4000)
                    except Exception: pass
                return f"[BROWSER] Typed '{text}' in input field '{label_or_selector}'." + (" Enter pressed." if press_enter else "")
        except Exception:
            pass

        # Fallback: standard finding
        loc = reader.find_element(label_or_selector)
        if loc is None:
            # Try raw selector
            try:
                loc = page.locator(label_or_selector).first
            except Exception:
                return f"[BROWSER] Could not find any input field matching '{label_or_selector}'."
        
        try:
            loc.fill(text, timeout=2000)
            if press_enter:
                loc.press("Enter")
                try: page.wait_for_load_state("domcontentloaded", timeout=4000)
                except Exception: pass
            return f"[BROWSER] Typed '{text}' in '{label_or_selector}'." + (" Enter pressed." if press_enter else "")
        except Exception as fill_err:
            return (
                f"[BROWSER] Error: Found an element for '{label_or_selector}', but it is not a text field. "
                "It is likely a button or div. Please try a more specific CSS selector for the input element itself "
                "(e.g., 'input#search' or 'textarea[name=\"q\"]'), or use BROWSER__get_inputs() to check field IDs."
            )
            
    except Exception as e:
        return f"[BROWSER] type_in_field error: {e}"


def scroll(direction: str = "down", amount: int = 300) -> str:
    """
    Scroll the page.
    :param direction: 'up' or 'down'
    :param amount: Pixels to scroll (default 300)
    """
    page = engine.get_page()
    if page is None:
        return engine._INSTALL_MSG
    try:
        delta = amount if direction.lower() == "down" else -amount
        page.evaluate(f"window.scrollBy(0, {delta})")
        return f"[BROWSER] Scrolled {direction} by {amount}px."
    except Exception as e:
        return f"[BROWSER] scroll error: {e}"


def press_key(key: str) -> str:
    """
    Press a keyboard key on the current focused element.
    :param key: e.g. 'Enter', 'Escape', 'Tab', 'ArrowDown'
    """
    page = engine.get_page()
    if page is None:
        return engine._INSTALL_MSG
    try:
        page.keyboard.press(key)
        return f"[BROWSER] Key pressed: '{key}'"
    except Exception as e:
        return f"[BROWSER] press_key error: {e}"


def run_js(code: str) -> str:
    """
    Execute raw JavaScript in the browser context.
    Returns the result as a string.
    :param code: JavaScript expression to evaluate, e.g. 'document.title'
    """
    page = engine.get_page()
    if page is None:
        return engine._INSTALL_MSG
    try:
        result = page.evaluate(code)
        return f"[BROWSER] JS result: {result}"
    except Exception as e:
        return f"[BROWSER] run_js error: {e}"


def take_screenshot() -> str:
    """
    Take a screenshot of the current browser viewport and save it to hecos/media/Hecos_screenshots.
    The path is returned so the vision AI can analyze it.
    """
    page = engine.get_page()
    if page is None:
        return engine._INSTALL_MSG
    try:
        hecos_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        save_dir = os.path.join(hecos_root, "media", "Hecos_screenshots")
        os.makedirs(save_dir, exist_ok=True)
        filename = f"hecos_browser_{int(time.time())}.png"
        full_path = os.path.join(save_dir, filename)
        page.screenshot(path=full_path, full_page=False)
        logger.info(f"[BROWSER] Screenshot saved: {full_path}")
        return f"[BROWSER] Browser screenshot saved: {full_path}"
    except Exception as e:
        return f"[BROWSER] take_screenshot error: {e}"


def go_back() -> str:
    """Navigate the browser back to the previous page."""
    page = engine.get_page()
    if page is None:
        return engine._INSTALL_MSG
    try:
        page.go_back(wait_until="domcontentloaded")
        return f"[BROWSER] Navigated back. Now at: {page.url}"
    except Exception as e:
        return f"[BROWSER] go_back error: {e}"
