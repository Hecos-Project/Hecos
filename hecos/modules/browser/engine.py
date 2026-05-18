"""
browser/engine.py
Playwright browser lifecycle manager — persistent singleton for Hecos.
"""

import os

from hecos.core.logging import logger

_PLAYWRIGHT = None
_BROWSER = None
_PAGE = None
_PW_INSTANCE = None
_LAST_ERROR = ""

_INSTALL_MSG = (
    "Playwright or Chromium binaries are missing. "
    "Please run: 'python -m playwright install chromium' in your terminal."
)


def _is_available() -> bool:
    try:
        import playwright  # noqa
        return True
    except ImportError:
        return False


def _ensure_chromium(pw_instance=None):
    """Verify Playwright Chromium binary is installed. Returns path or raises Error."""
    try:
        from playwright.sync_api import sync_playwright
        
        def _check(pw):
            try:
                path = pw.chromium.executable_path
                if not path or not os.path.exists(path):
                    raise FileNotFoundError("Missing binary")
                return path
            except Exception:
                raise FileNotFoundError(
                    "Chromium binaries are missing from the system. "
                    "To fix this, please run: 'python -m playwright install chromium' in your terminal."
                )
                
        if pw_instance:
            return _check(pw_instance)
        else:
            with sync_playwright() as pw:
                return _check(pw)
    except ImportError:
        raise ImportError(
            "Playwright library is not installed in the project environment. "
            "Please run: 'pip install playwright' inside Hecos root."
        )


def launch(headless: bool = False, block_ads: bool = True, timeout: int = 10000, mode: str = "app_mode", cdp_port: int = 9222) -> bool:
    """Start or connect to the Playwright browser. Returns True on success."""
    global _PLAYWRIGHT, _BROWSER, _PAGE, _PW_INSTANCE, _LAST_ERROR
    
    _LAST_ERROR = ""
    if not _is_available():
        _LAST_ERROR = _INSTALL_MSG
        return False
    
    try:
        from playwright.sync_api import sync_playwright
        
        if _BROWSER and _BROWSER.is_connected():
            logger.debug(f"[BROWSER] Already connected (Mode: {mode}).")
            return True
            
        _PW_INSTANCE = sync_playwright().start()
        
        if mode == "cdp_mode":
            # Connect to existing Chrome instance via CDP
            logger.info(f"[BROWSER] Attempting CDP connection → http://localhost:{cdp_port}")
            try:
                endpoint = f"http://localhost:{cdp_port}"
                _BROWSER = _PW_INSTANCE.chromium.connect_over_cdp(endpoint)
                ctx = _BROWSER.contexts[0] if _BROWSER.contexts else _BROWSER.new_context()
                _PAGE = ctx.pages[0] if ctx.pages else ctx.new_page()
                _PAGE.set_default_timeout(timeout)
                ctx_count = len(_BROWSER.contexts)
                page_count = sum(len(c.pages) for c in _BROWSER.contexts)
                logger.info(f"[BROWSER] ✅ CDP connected on port {cdp_port} — contexts={ctx_count}, pages={page_count}")
                return True
            except Exception as cdp_e:
                _LAST_ERROR = (
                    f"CDP Takeover failed: Chrome must be launched with "
                    f"'--remote-debugging-port={cdp_port}'. "
                    f"Use the '🤖 Open AI-Ready Chrome' button in the tray icon. Details: {cdp_e}"
                )
                logger.error(f"[BROWSER] ❌ CDP connection failed on port {cdp_port}: {cdp_e}")
                logger.warning(f"[BROWSER] Hint: Launch Chrome via the tray icon '🤖 Open AI-Ready Chrome' to enable CDP mode.")
                return False
        else:
            # Standard background isolated Chromium
            try:
                _ensure_chromium(_PW_INSTANCE)
            except Exception as er:
                _LAST_ERROR = str(er)
                return False
                
            _BROWSER = _PW_INSTANCE.chromium.launch(
                headless=headless,
                channel="chrome",
                args=[
                    "--no-sandbox",
                    "--disable-infobars",
                    "--disable-blink-features=AutomationControlled",
                ]
            )
            ctx = _BROWSER.new_context(
                viewport={"width": 1280, "height": 800},
                ignore_https_errors=True,
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0 Safari/537.36"
                )
            )
            if block_ads:
                ctx.route("**/*.{png,jpg,gif,webp,svg}", lambda r: r.abort())  # type: ignore
                # Block known ad hosts
                ctx.route(
                    "**/googleadservices/**,**/doubleclick.net/**,**/googlesyndication.com/**",
                    lambda r: r.abort()
                )
            _PAGE = ctx.new_page()
            _PAGE.set_default_timeout(timeout)
            logger.info("[BROWSER] Isolated Chromium (App Mode) launched.")
            return True
    except Exception as e:
        _LAST_ERROR = str(e)
        logger.error(f"[BROWSER] Launch error: {e}")
        return False


def close():
    """Close the browser and stop Playwright."""
    global _BROWSER, _PAGE, _PW_INSTANCE
    try:
        if _BROWSER:
            _BROWSER.close()
        if _PW_INSTANCE:
            _PW_INSTANCE.stop()
    except Exception as e:
        logger.debug(f"[BROWSER] Close error: {e}")
    finally:
        _BROWSER = None
        _PAGE = None
        _PW_INSTANCE = None


def get_page():
    """Return the current active Playwright Page object. Launches if not running."""
    global _PAGE
    if _PAGE is None or _PAGE.is_closed():
        if not launch():
            return None
    return _PAGE


def new_tab(url: str = "about:blank"):
    """Open a new tab and navigate to url. Returns the new Page object."""
    global _PAGE
    page = get_page()
    if page is None:
        return None
    ctx = page.context
    _PAGE = ctx.new_page()
    if url and url != "about:blank":
        _PAGE.goto(url, wait_until="domcontentloaded")
    return _PAGE


def get_last_error() -> str:
    """Return the last launch/setup error message."""
    return _LAST_ERROR


def is_running() -> bool:
    """Check if the browser is currently running."""
    return _BROWSER is not None and _BROWSER.is_connected()


def find_chrome_executable() -> str:
    """Search for common Chrome or Edge installation paths."""
    import os
    user_local = os.environ.get("LOCALAPPDATA", "")
    paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.join(user_local, r"Google\Chrome\Application\chrome.exe"),
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    for p in paths:
        if os.path.exists(p):
            return p
    return ""


def launch_external_browser(port: int = 9222) -> str:
    """Launches the system browser with remote debugging enabled."""
    import subprocess
    import os
    
    exe = find_chrome_executable()
    if not exe:
        return "Errore: Non ho trovato Google Chrome o Microsoft Edge installati nei percorsi standard."
    
    # Use a dedicated user data dir to avoid conflicts with open instances
    user_data = os.path.join(os.environ.get("TEMP", "."), "hecos_browser_profile")
    if not os.path.exists(user_data):
        os.makedirs(user_data, exist_ok=True)
        
    cmd = [
        exe,
        f"--remote-debugging-port={port}",
        f"--user-data-dir={user_data}",
        "--no-first-run",
        "--no-default-browser-check"
    ]
    
    try:
        # 0x00000008 is DETACHED_PROCESS on Windows. 
        # This allows the browser to keep running even if the Hecos service restarts, 
        # and avoids inheriting/opening a console window.
        subprocess.Popen(cmd, creationflags=0x00000008, close_fds=True)
        return f"Browser lanciato con successo sulla porta {port}."
    except Exception as e:
        return f"Errore durante il lancio del browser: {e}"


def list_tabs() -> list:
    """Returns a list of all open tabs/pages in the current browser context."""
    global _BROWSER
    if not _BROWSER:
        logger.debug("[BROWSER] list_tabs called but _BROWSER is None (CDP not connected).")
        return []

    tabs = []
    try:
        ctx_count = len(_BROWSER.contexts)
        logger.debug(f"[BROWSER] list_tabs — browser contexts: {ctx_count}")
        for context in _BROWSER.contexts:
            for idx, page in enumerate(context.pages):
                try:
                    title = page.title()
                    url = page.url()
                    is_active = page == _PAGE
                    tabs.append({"id": idx, "title": title, "url": url, "active": is_active})
                    logger.debug(f"[BROWSER] Tab [{idx}] title='{title}' active={is_active}")
                except Exception as pe:
                    logger.debug(f"[BROWSER] Tab [{idx}] unreadable: {pe}")
        logger.info(f"[BROWSER] list_tabs → {len(tabs)} tabs found")
    except Exception as e:
        logger.error(f"[BROWSER] list_tabs error: {e}")
    return tabs


def switch_tab(index: int) -> bool:
    """Switches the active page handle to the tab at the given index."""
    global _BROWSER, _PAGE
    if not _BROWSER:
        logger.warning("[BROWSER] switch_tab called but browser is not connected.")
        return False
        
    try:
        pages = []
        for context in _BROWSER.contexts:
            pages.extend(context.pages)
        
        logger.debug(f"[BROWSER] switch_tab({index}) — available pages: {len(pages)}")
        if 0 <= index < len(pages):
            _PAGE = pages[index]
            _PAGE.bring_to_front()
            logger.info(f"[BROWSER] ✅ Switched to tab [{index}]: '{_PAGE.title()}'")
            return True
        else:
            logger.warning(f"[BROWSER] switch_tab({index}) — index out of range (max: {len(pages) - 1})")
    except Exception as e:
        logger.error(f"[BROWSER] Switch tab error: {e}")
    return False
