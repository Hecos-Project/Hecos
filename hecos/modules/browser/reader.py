"""
browser/reader.py
DOM Intelligence Layer — reads structured content from the current page.
"""

from hecos.core.logging import logger
from . import engine


def get_page_text(max_chars: int = 4000) -> str:
    """Return all visible text from the current page, trimmed to max_chars."""
    page = engine.get_page()
    if page is None:
        return engine._INSTALL_MSG
    try:
        text = page.evaluate("() => document.body.innerText")
        if len(text) > max_chars:
            text = text[:max_chars] + f"\n...[truncated, {len(text) - max_chars} more chars]"
        return text.strip()
    except Exception as e:
        logger.error(f"[BROWSER] get_page_text error: {e}")
        return f"[BROWSER] Could not read page text: {e}"


def get_links(max_results: int = 30) -> str:
    """Return all hyperlinks on the current page as a numbered list (label → url)."""
    page = engine.get_page()
    if page is None:
        return engine._INSTALL_MSG
    try:
        links = page.evaluate("""() => {
            return Array.from(document.querySelectorAll('a[href]'))
                .map(a => ({ label: a.innerText.trim().slice(0, 80), href: a.href }))
                .filter(l => l.label && l.href.startsWith('http'))
                .slice(0, 50);
        }""")
        if not links:
            return "[BROWSER] No links found on this page."
        result = f"[BROWSER] Links on current page ({len(links[:max_results])}):\n"
        result += "\n".join(f"  [{i}] {l['label']} → {l['href']}" for i, l in enumerate(links[:max_results]))
        return result
    except Exception as e:
        return f"[BROWSER] get_links error: {e}"


def find_element(text_or_aria: str):
    """
    Find a page element by its visible text or aria-label.
    Returns the Playwright Locator or None.
    """
    page = engine.get_page()
    if page is None:
        return None
    try:
        # Try aria-label first (most common for buttons/icons on Google/YouTube)
        loc = page.get_by_label(text_or_aria)
        if loc.count() > 0:
            return loc.first
        # Try visible text
        loc = page.get_by_text(text_or_aria, exact=False)
        if loc.count() > 0:
            return loc.first
        # Try placeholder (for inputs)
        loc = page.get_by_placeholder(text_or_aria)
        if loc.count() > 0:
            return loc.first
        return None
    except Exception as e:
        logger.debug(f"[BROWSER] find_element error: {e}")
        return None


def get_inputs() -> str:
    """Return all form inputs (text fields, buttons) on the current page."""
    page = engine.get_page()
    if page is None:
        return engine._INSTALL_MSG
    try:
        inputs = page.evaluate("""() => {
            const fields = [];
            document.querySelectorAll('input, textarea, button, select').forEach(el => {
                fields.push({
                    tag: el.tagName,
                    type: el.type || '',
                    name: el.name || el.id || el.placeholder || el.ariaLabel || el.innerText?.trim() || ''
                });
            });
            return fields.slice(0, 40);
        }""")
        if not inputs:
            return "[BROWSER] No input elements found on this page."
        result = "[BROWSER] Interactive elements:\n"
        result += "\n".join(f"  [{i}] <{f['tag'].lower()} type={f['type']}> {f['name']}" for i, f in enumerate(inputs))
        return result
    except Exception as e:
        return f"[BROWSER] get_inputs error: {e}"


def get_current_url() -> str:
    """Return the URL currently loaded in the browser."""
    page = engine.get_page()
    if page is None:
        return engine._INSTALL_MSG
    try:
        return f"[BROWSER] Current URL: {page.url}"
    except Exception as e:
        return f"[BROWSER] get_current_url error: {e}"


def get_title() -> str:
    """Return the title of the current page."""
    page = engine.get_page()
    if page is None:
        return engine._INSTALL_MSG
    try:
        return f"[BROWSER] Page title: {page.title()}"
    except Exception as e:
        return f"[BROWSER] get_title error: {e}"
