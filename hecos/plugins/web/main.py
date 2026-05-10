try:
    from hecos.core.i18n import translator
except ImportError:
    class DummyTranslator:
        def t(self, key, **kwargs): return key
    translator = DummyTranslator()

from .search import open_url_tool, search_web_tool, fetch_page_content_tool, search_and_read_tool
from .clipboard import get_clipboard, set_clipboard

class WebTools:
    """
    Hecos Web Plugin — Browsing, search, content reading, and clipboard.
    """

    def __init__(self):
        self.tag = "WEB"
        self.desc = translator.t("plugin_web_desc")
        self.status = translator.t("plugin_web_status_online")
        self.routing_instructions = (
            "If the user asks you to interact with a website or application that is ALREADY OPEN on their screen "
            "(e.g., 'click the next video', 'change song', 'scroll down'), DO NOT use the WEB tools. "
            "Instead, use WEBCAM__desktop_screenshot and the AUTOMATION tools to physically interact with the existing window."
        )

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

    # ── Public Tools ───────────────────────────────────────────────────────────

    def open_url(self, url: str) -> str:
        """
        Opens a specific website in the default browser.
        NOTE: this only opens the browser. Use fetch_page_content to read the page content.
        :param url: The website address to open (e.g., 'youtube.com', 'wikipedia.org').
        """
        return open_url_tool(url, self.tag)

    def search_web(self, query: str) -> str:
        """
        Opens a browser search for a query.
        NOTE: use search_and_read instead if you need the actual text content of results.
        :param query: The terms to search for on the internet.
        """
        return search_web_tool(query, self.tag)

    def fetch_page_content(self, url: str, max_chars_override: int = None) -> str:
        """
        Fetches a web page and returns its readable text content.
        Use this to read articles, documentation, Wikipedia pages, or any URL.
        Does NOT open a browser window — reads and returns the text directly.
        :param url: Full URL of the page (e.g., 'https://en.wikipedia.org/wiki/Python').
        :param max_chars_override: Optional limit for content length (overrides config).
        """
        return fetch_page_content_tool(url, self.tag, max_chars_override=max_chars_override)

    def search_and_read(self, query: str, max_results: int = 3) -> str:
        """
        Searches the web using DuckDuckGo and reads the text content of the top results.
        Use this when you need CURRENT information, facts, news, prices, or live data.
        Does NOT open any browser window — results are returned as text directly.
        :param query: The search terms (e.g., 'Python 3.13 new features', 'weather Rome today').
        :param max_results: How many pages to read (1–5). Default: 3.
        """
        return search_and_read_tool(query, self.tag, max_results=max_results)

    def get_clipboard(self) -> str:
        """
        Returns the current text from the system clipboard.
        Use this when the user says 'use what I just copied' or 'fix this code'.
        """
        return get_clipboard()

    def set_clipboard(self, text: str) -> str:
        """
        Copies the given text to the system clipboard.
        :param text: The text to copy to clipboard.
        """
        return set_clipboard(text)


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