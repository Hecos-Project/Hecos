"""
browser/main.py
BrowserTools — LLM-callable tool interface for the Playwright browser module.
"""

try:
    from hecos.core.i18n import translator
    from hecos.app.config import ConfigManager
except ImportError:
    class DummyTranslator:
        def t(self, key, **kwargs): return key
    translator = DummyTranslator()
    class DummyConfigMgr:
        def get_module_config(self, tag, key, default): return default
    def ConfigManager(): return DummyConfigMgr()

from . import engine
from . import reader
from . import interactor
import queue
import threading
from functools import wraps

class PlaywrightWorker:
    """Dedicated background thread to safely run Playwright Sync API without asyncio clashes."""
    def __init__(self):
        self.q = queue.Queue()
        self.t = threading.Thread(target=self._run, daemon=True)
        self.t.start()
        
    def _run(self):
        while True:
            func, args, kwargs, result_q = self.q.get()
            import threading, asyncio
            
            try:
                loop_status = str(asyncio.get_running_loop())
            except Exception:
                loop_status = "None"
            
            print(f"--- [WORKER DEBUG] Thread: {threading.current_thread().name}, Loop: {loop_status}, Func: {func.__name__} ---")
            
            try:
                res = func(*args, **kwargs)
                result_q.put((True, res))
            except Exception as e:
                import traceback
                print(f"--- [WORKER DEBUG ERROR] ---")
                traceback.print_exc()
                result_q.put((False, e))
                
    def execute(self, func, *args, **kwargs):
        res_q = queue.Queue()
        self.q.put((func, args, kwargs, res_q))
        success, res = res_q.get()
        if not success:
            raise res
        return res

_WORKER = PlaywrightWorker()

def bypass_playwright_async_check(func):
    """
    Decorator to wrap BROWSER tool methods.
    Proxies all tool logic securely into a dedicated background OS thread, 
    isolating Playwright's Sync API completely from the Hecos asyncio main loop.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        return _WORKER.execute(func, *args, **kwargs)
    return wrapper


class BrowserTools:
    """
    Hecos BROWSER — A persistent, programmable Chromium browser controlled by the AI.
    Uses Playwright to navigate, read DOM content, click elements, and execute JavaScript
    without relying on pixel coordinates or screenshots.
    """

    def __init__(self):
        self.tag = "BROWSER"
        self.desc = (
            "Programmable AI-controlled browser (Playwright Chromium). "
            "Navigate URLs, read page content, click elements and fill forms "
            "without vision or coordinate guessing."
        )
        self.routing_instructions = (
            "BROWSER CAPABILITY: You have your own programmable browser! "
            "When the user asks to browse a website, open a URL, read page content, "
            "or interact with a web form, use BROWSER tools — NOT the WEB plugin. "
            "WORKFLOW: BROWSER__open_url → BROWSER__get_page_text or BROWSER__get_links "
            "→ BROWSER__click_element or BROWSER__type_in_field. "
            "Prefer click_element(text) over screenshots for structured pages. "
            "Only use BROWSER__screenshot if you need to visually analyze the page."
        )
        self.status = "ONLINE"

        self.config_schema = {
            "headless": {
                "type": "bool",
                "default": False,
                "description": "Run the browser invisibly in background (true) or visibly (false)."
            },
            "browser_type": {
                "type": "str",
                "default": "chromium",
                "options": ["chromium", "firefox"],
                "description": "Browser engine to use."
            },
            "default_timeout": {
                "type": "int",
                "default": 10000,
                "min": 1000,
                "max": 60000,
                "description": "Timeout in milliseconds for page element operations."
            },
            "block_ads": {
                "type": "bool",
                "default": True,
                "description": "Block advertising networks for faster page loads."
            }
        }

    def _get_config(self):
        try:
            from hecos.app.config import ConfigManager
            root_cfg = ConfigManager().config
            cfg = root_cfg.get("BROWSER", {})
            if not cfg:
                cfg = root_cfg.get("plugins", {}).get("BROWSER", {})
                
            return {
                "headless": cfg.get("headless", False),
                "block_ads": cfg.get("block_ads", True),
                "timeout": cfg.get("default_timeout", 10000),
                "mode": cfg.get("browser_engine_mode", "app_mode"),
                "cdp_port": cfg.get("cdp_port", 9222)
            }
        except Exception:
            return {"headless": False, "block_ads": True, "timeout": 10000, "mode": "app_mode", "cdp_port": 9222}

    def _ensure_running(self):
        if not engine.is_running():
            cfg = self._get_config()
            if not engine.launch(
                headless=cfg["headless"],
                block_ads=cfg["block_ads"],
                timeout=cfg["timeout"],
                mode=cfg["mode"],
                cdp_port=cfg["cdp_port"]
            ):
                return f"[BROWSER] ERROR: {engine.get_last_error()}"
        return None

    # ─── Navigation ────────────────────────────────────────────────────────────

    @bypass_playwright_async_check
    def open_url(self, url: str) -> str:
        """
        Opens a URL in the Hecos browser. The browser will become visible if not already running.
        :param url: The full URL to navigate to, e.g. 'https://youtube.com' or 'youtube.com'.
        """
        err = self._ensure_running()
        if err: return err
        return interactor.navigate(url)

    @bypass_playwright_async_check
    def get_current_url(self) -> str:
        """Returns the URL currently loaded in the Hecos browser."""
        err = self._ensure_running()
        if err: return err
        return reader.get_current_url()

    @bypass_playwright_async_check
    def go_back(self) -> str:
        """Navigate the browser back to the previous page."""
        err = self._ensure_running()
        if err: return err
        return interactor.go_back()

    # ─── Page Reading ──────────────────────────────────────────────────────────

    @bypass_playwright_async_check
    def get_page_text(self, max_chars: int = 4000) -> str:
        """
        Returns all visible text from the current page.
        Use this to understand page content before searching for elements.
        :param max_chars: Maximum characters to return (default 4000).
        """
        err = self._ensure_running()
        if err: return err
        return reader.get_page_text(max_chars)

    @bypass_playwright_async_check
    def get_links(self) -> str:
        """
        Returns all hyperlinks on the current page as a numbered list (label → URL).
        Use this to find links to navigate to.
        """
        err = self._ensure_running()
        if err: return err
        return reader.get_links()

    @bypass_playwright_async_check
    def get_inputs(self) -> str:
        """
        Lists all interactive form elements (input fields, buttons) on the current page.
        Use this to identify field names before calling type_in_field.
        """
        err = self._ensure_running()
        if err: return err
        return reader.get_inputs()

    @bypass_playwright_async_check
    def get_title(self) -> str:
        """Returns the title of the current browser page."""
        err = self._ensure_running()
        if err: return err
        return reader.get_title()

    # ─── Interaction ───────────────────────────────────────────────────────────

    @bypass_playwright_async_check
    def click_element(self, text_or_selector: str) -> str:
        """
        Clicks an element by its visible text, aria-label, or CSS selector.
        Preferred over coordinate-based clicking.
        :param text_or_selector: Visible text, aria-label, or CSS selector of the target.
        """
        err = self._ensure_running()
        if err: return err
        return interactor.click_element(text_or_selector)

    @bypass_playwright_async_check
    def type_in_field(self, label_or_selector: str, text: str, press_enter: bool = False) -> str:
        """
        Finds an input field by its label, placeholder or selector, and types text into it.
        :param label_or_selector: Label, placeholder, aria-label, or CSS selector of the field.
        :param text: The text to type.
        :param press_enter: If true, presses Enter after typing (useful for search boxes).
        """
        err = self._ensure_running()
        if err: return err
        return interactor.type_in_field(label_or_selector, text, press_enter)

    @bypass_playwright_async_check
    def scroll(self, direction: str = "down", amount: int = 300) -> str:
        """
        Scrolls the browser page up or down.
        :param direction: 'down' or 'up'.
        :param amount: Number of pixels to scroll.
        """
        err = self._ensure_running()
        if err: return err
        return interactor.scroll(direction, amount)

    @bypass_playwright_async_check
    def press_key(self, key: str) -> str:
        """
        Presses a keyboard key in the browser (e.g. 'Enter', 'Escape', 'ArrowDown').
        :param key: Key name following standard web key names.
        """
        err = self._ensure_running()
        if err: return err
        return interactor.press_key(key)

    @bypass_playwright_async_check
    def run_js(self, code: str) -> str:
        """
        Executes JavaScript code in the browser and returns the result.
        Powerful for extracting data or triggering browser actions.
        :param code: JavaScript expression, e.g. 'document.title' or 'document.querySelector("h1").innerText'.
        """
        err = self._ensure_running()
        if err: return err
        return interactor.run_js(code)

    def screenshot(self) -> str:
        """
        Takes a screenshot of the current browser viewport.
        The image is saved to hecos/media/Hecos_screenshots and the path is returned for vision analysis.
        """
        err = self._ensure_running()
        if err: return err
        return interactor.take_screenshot()

    def close(self) -> str:
        """Closes the Hecos browser window."""
        engine.close()
        return "[BROWSER] Browser closed."

    def launch_external(self) -> str:
        """
        Attempts to find and launch the user's system browser (Chrome/Edge) 
        with remote debugging enabled on the configured CDP port.
        """
        cfg = self._get_config()
        return engine.launch_external_browser(cfg.get("cdp_port", 9222))

    def list_tabs(self) -> str:
        """
        Lists all open tabs in the current browser.
        Primary: uses CDP (Playwright) if Chrome was launched in AI-Ready mode.
        Fallback: uses Windows Accessibility API when CDP is not connected.
        """
        # --- Try CDP first ---
        tabs = engine.list_tabs()
        if tabs:
            lines = ["[BROWSER] Open browser tabs (CDP mode — full control available):"]
            for t in tabs:
                status = " ★ ACTIVE" if t["active"] else ""
                lines.append(f"  [{t['id']}] {t['title']} — {t['url']}{status}")
            lines.append("\nUse BROWSER__switch_tab(index) to focus the desired tab.")
            return "\n".join(lines)

        # --- Fallback: Windows Accessibility API ---
        try:
            from hecos.modules.automation.ui_automation import _get_chrome_tabs_via_uia
            win_tabs = _get_chrome_tabs_via_uia()
            if win_tabs:
                lines = [
                    "[BROWSER] CDP not active — showing tabs via Windows Accessibility (read-only, no direct DOM control).",
                    "Use AUTOMATION__focus_browser_tab(title_fragment) to switch to the desired tab.",
                    ""
                ]
                for i, t in enumerate(win_tabs):
                    lines.append(f"  [{i}] {t}")
                return "\n".join(lines)
        except Exception:
            pass

        return (
            "[BROWSER] No browser tabs found. "
            "Make sure Chrome or Edge is open. "
            "For full AI control launch Chrome via the '🤖 Open AI-Ready Chrome' button in the tray icon menu."
        )

    def switch_tab(self, index: int) -> str:
        """
        Switches to the tab with the specified numeric ID.
        :param index: The ID of the tab to focus (from list_tabs).
        """
        if engine.switch_tab(index):
            return f"[BROWSER] Switched to tab [{index}]."
        return f"[BROWSER] Could not switch to tab [{index}] — index out of range or CDP not connected. Try AUTOMATION__focus_browser_tab instead."

# ── Singleton ──────────────────────────────────────────────────────────────────
tools = BrowserTools()


def info():
    return {"tag": tools.tag, "desc": tools.desc}


def status():
    return tools.status


def get_plugin():
    return tools
