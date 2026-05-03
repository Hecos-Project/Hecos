import webbrowser
import urllib.parse

try:
    from hecos.core.logging import logger
    from hecos.core.i18n import translator
    from app.config import ConfigManager
except ImportError:
    class DummyLogger:
        def debug(self, *args, **kwargs): print("[WEB_DEBUG]", *args)
        def error(self, *args, **kwargs): print("[WEB_ERR]", *args)
        def info(self, *args, **kwargs): print("[WEB_INFO]", *args)
        def warning(self, *args, **kwargs): print("[WEB_WARNING]", *args)
    logger = DummyLogger()

    class DummyTranslator:
        def t(self, key, **kwargs): return key
    translator = DummyTranslator()

    class DummyConfig:
        def get_plugin_config(self, tag, key, default): return default
    def FakeConfigManager(): return DummyConfig()
    ConfigManager = FakeConfigManager


# ── Helpers ────────────────────────────────────────────────────────────────────

def _ensure_https(url: str) -> str:
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def _extract_text(html: str, max_chars: int = 4000) -> str:
    """Extract readable text from HTML. Tries trafilatura → BeautifulSoup → regex."""
    try:
        import trafilatura
        result = trafilatura.extract(html, include_comments=False, include_tables=False)
        if result and len(result.strip()) > 100:
            return result.strip()[:max_chars]
    except ImportError:
        pass

    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        lines = [l for l in text.splitlines() if len(l.strip()) > 20]
        return "\n".join(lines)[:max_chars]
    except ImportError:
        pass

    import re
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)
    return text.strip()[:max_chars]


# ── Plugin Class ────────────────────────────────────────────────────────────────

class WebTools:
    """
    Hecos Web Plugin — Browsing, search, content reading, and clipboard.
    """

    def __init__(self):
        self.tag = "WEB"
        self.desc = translator.t("plugin_web_desc")
        self.status = translator.t("plugin_web_status_online")

        self.config_schema = {
            "search_engine": {
                "type": "str",
                "default": "google",
                "options": ["google", "duckduckgo", "bing"],
                "description": translator.t("plugin_web_search_engine_desc")
            },
            "use_https": {
                "type": "bool",
                "default": True,
                "description": translator.t("plugin_web_use_https_desc")
            },
            "open_in_new_tab": {
                "type": "bool",
                "default": False,
                "description": translator.t("plugin_web_open_in_new_tab_desc")
            },
            "fetch_timeout": {
                "type": "int",
                "default": 10,
                "description": "HTTP timeout in seconds for fetch_page_content and search_and_read."
            },
            "max_content_chars": {
                "type": "int",
                "default": 4000,
                "description": "Max characters returned by fetch_page_content and search_and_read."
            }
        }

    # ── Private helpers ────────────────────────────────────────────────────────

    def _get_search_url(self, query: str) -> str:
        cfg = ConfigManager()
        engine = cfg.get_plugin_config(self.tag, "search_engine", "google")
        q = urllib.parse.quote(query)
        if engine == "duckduckgo":
            return f"https://duckduckgo.com/?q={q}"
        elif engine == "bing":
            return f"https://www.bing.com/search?q={q}"
        return f"https://www.google.com/search?q={q}"

    def _open_target_url(self, url: str):
        cfg = ConfigManager()
        use_https = cfg.get_plugin_config(self.tag, "use_https", True)
        open_new = cfg.get_plugin_config(self.tag, "open_in_new_tab", False)
        if use_https and not url.startswith(("http://", "https://")):
            url = "https://" + url
        if open_new:
            webbrowser.open_new_tab(url)
        else:
            webbrowser.open(url)

    def _http_get(self, url: str) -> str | None:
        """Fetches raw HTML from a URL using httpx → requests → urllib fallback."""
        cfg = ConfigManager()
        timeout = cfg.get_plugin_config(self.tag, "fetch_timeout", 10)
        headers = {"User-Agent": "Mozilla/5.0 (compatible; Hecos/1.0; +https://hecos.ai)"}
        try:
            import httpx
            r = httpx.get(url, headers=headers, timeout=timeout, follow_redirects=True)
            r.raise_for_status()
            return r.text
        except ImportError:
            pass
        try:
            import requests
            r = requests.get(url, headers=headers, timeout=timeout)
            r.raise_for_status()
            return r.text
        except ImportError:
            pass
        try:
            import urllib.request as ureq
            req = ureq.Request(url, headers=headers)
            with ureq.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            logger.error(f"[WEB] HTTP fetch failed for {url}: {e}")
            return None

    # ── Public Tools ───────────────────────────────────────────────────────────

    def open_url(self, url: str) -> str:
        """
        Opens a specific website in the default browser.
        NOTE: this only opens the browser. Use fetch_page_content to read the page content.
        :param url: The website address to open (e.g., 'youtube.com', 'wikipedia.org').
        """
        addr = url.strip()
        logger.debug(f"PLUGIN_{self.tag}", f"Opening site: {addr}")
        try:
            self._open_target_url(addr)
            return translator.t("plugin_web_open_success", url=addr)
        except Exception as e:
            logger.error(f"PLUGIN_{self.tag}: Error: {e}")
            return translator.t("plugin_web_error_network", error=str(e))

    def search_web(self, query: str) -> str:
        """
        Opens a browser search for a query.
        NOTE: use search_and_read instead if you need the actual text content of results.
        :param query: The terms to search for on the internet.
        """
        ricerca = query.strip()
        logger.debug(f"PLUGIN_{self.tag}", f"Searching: {ricerca}")
        try:
            url_ricerca = self._get_search_url(ricerca)
            self._open_target_url(url_ricerca)
            return translator.t("plugin_web_search_success", query=ricerca)
        except Exception as e:
            logger.error(f"PLUGIN_{self.tag}: Error: {e}")
            return translator.t("plugin_web_error_network", error=str(e))

    def fetch_page_content(self, url: str, max_chars_override: int = None) -> str:
        """
        Fetches a web page and returns its readable text content.
        Use this to read articles, documentation, Wikipedia pages, or any URL.
        Does NOT open a browser window — reads and returns the text directly.
        :param url: Full URL of the page (e.g., 'https://en.wikipedia.org/wiki/Python').
        :param max_chars_override: Optional limit for content length (overrides config).
        """
        url = _ensure_https(url)
        logger.info(f"[WEB] fetch_page_content: {url}")
        html = self._http_get(url)
        if html is None:
            return f"[WEB] Failed to fetch page: {url}. Check the URL and network connection."
        
        cfg = ConfigManager()
        max_chars = cfg.get_plugin_config(self.tag, "max_content_chars", 4000)
        
        # Robustness: force integer types
        try:
            if max_chars_override is not None:
                max_chars = int(max_chars_override)
            else:
                max_chars = int(max_chars)
        except (ValueError, TypeError):
            max_chars = 4000

        text = _extract_text(html, max_chars)
        if not text or len(text.strip()) < 50:
            return f"[WEB] Page fetched but no readable content found at: {url}"
        return f"📄 Content from {url}:\n\n{text}"

    def search_and_read(self, query: str, max_results: int = 3) -> str:
        """
        Searches the web using DuckDuckGo and reads the text content of the top results.
        Use this when you need CURRENT information, facts, news, prices, or live data.
        Does NOT open any browser window — results are returned as text directly.
        :param query: The search terms (e.g., 'Python 3.13 new features', 'weather Rome today').
        :param max_results: How many pages to read (1–5). Default: 3.
        """
        # Robustness: The LLM often sends arguments as strings. Force integer for comparison.
        try:
            max_res_int = int(max_results)
        except (ValueError, TypeError):
            max_res_int = 3

        q = query.strip()
        logger.info(f"[WEB] search_and_read: {q}")
        search_url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(q)}"
        html = self._http_get(search_url)
        if html is None:
            return "[WEB] Could not reach DuckDuckGo. Check your internet connection."

        import re
        raw_links = re.findall(r'uddg=(https?%3A[^&"]+)', html)
        urls = []
        for raw in raw_links:
            try:
                decoded = urllib.parse.unquote(raw)
                if any(s in decoded for s in ["duckduckgo.com", "doubleclick", "adservice", "ads."]):
                    continue
                urls.append(decoded)
            except Exception:
                continue
            if len(urls) >= max(1, min(max_res_int, 5)):
                break

        if not urls:
            return f"[WEB] No results found for: '{q}'. Try rephrasing."

        cfg = ConfigManager()
        try:
            max_chars = int(cfg.get_plugin_config(self.tag, "max_content_chars", 4000))
        except (ValueError, TypeError):
            max_chars = 4000
            
        per_page = max(800, max_chars // len(urls))

        results = [f"🔍 Search results for: \"{q}\"\n"]
        for i, url in enumerate(urls, 1):
            logger.info(f"[WEB] Reading result {i}/{len(urls)}: {url}")
            page_html = self._http_get(url)
            if page_html is None:
                results.append(f"[{i}] ⚠️  Could not read: {url}")
                continue
            text = _extract_text(page_html, per_page)
            if text and len(text.strip()) > 50:
                results.append(f"[{i}] 📄 {url}\n{text}\n")
            else:
                results.append(f"[{i}] ⚠️  No readable content at: {url}")

        return "\n---\n".join(results)

    def get_clipboard(self) -> str:
        """
        Returns the current text from the system clipboard.
        Use this when the user says 'use what I just copied' or 'fix this code'.
        """
        try:
            import pyperclip
            text = pyperclip.paste()
            if not text or not text.strip():
                return "[WEB] Clipboard is empty."
            return f"📋 Clipboard content:\n\n{text[:3000]}"
        except ImportError:
            return "[WEB] Clipboard requires pyperclip: pip install pyperclip"
        except Exception as e:
            return f"[WEB] Clipboard read error: {e}"

    def set_clipboard(self, text: str) -> str:
        """
        Copies the given text to the system clipboard.
        :param text: The text to copy to clipboard.
        """
        try:
            import pyperclip
            pyperclip.copy(text)
            preview = text[:80].replace("\n", " ")
            return f"📋 Copied to clipboard: \"{preview}{'...' if len(text) > 80 else ''}\""
        except ImportError:
            return "[WEB] Clipboard requires pyperclip: pip install pyperclip"
        except Exception as e:
            return f"[WEB] Clipboard write error: {e}"


# ── Singleton ──────────────────────────────────────────────────────────────────
tools = WebTools()


def info():
    return {"tag": tools.tag, "desc": tools.desc}


def status():
    return tools.status


def execute(comando: str) -> str:
    """Legacy shim for old tag-based routing."""
    c = comando.strip()
    c_lower = c.lower()
    if c_lower.startswith(("search:", "cerca:", "search_web:")):
        return tools.search_web(c.split(":", 1)[1].strip())
    elif c_lower.startswith(("url:", "apri:", "open_url:")):
        return tools.open_url(c.split(":", 1)[1].strip())
    elif c_lower.startswith(("fetch:", "read:", "fetch_page_content:")):
        return tools.fetch_page_content(c.split(":", 1)[1].strip())
    elif c_lower.startswith(("search_and_read:", "leggi:")):
        return tools.search_and_read(c.split(":", 1)[1].strip())
    return f"[WEB] Unknown legacy command: '{comando}'"