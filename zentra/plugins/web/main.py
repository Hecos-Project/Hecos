import webbrowser
import urllib.parse
import webbrowser
import urllib.parse
try:
    from core.logging import logger
    from core.i18n import translator
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
    
    # Per supportare ConfigManager()
    def FakeConfigManager(): return DummyConfig()
    ConfigManager = FakeConfigManager

class WebTools:
    """
    Plugin: Web Browsing
    Allows performing internet searches or opening specific websites in the browser.
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
            }
        }

    # --- METODI PRIVATI ---

    def _get_search_url(self, query: str) -> str:
        """Restituisce l'URL di ricerca configurato."""
        cfg = ConfigManager()
        engine = cfg.get_plugin_config(self.tag, "search_engine", "google")
        query_encoded = urllib.parse.quote(query)
        
        if engine == "google":
            return f"https://www.google.com/search?q={query_encoded}"
        elif engine == "duckduckgo":
            return f"https://duckduckgo.com/?q={query_encoded}"
        elif engine == "bing":
            return f"https://www.bing.com/search?q={query_encoded}"
        else:
            return f"https://www.google.com/search?q={query_encoded}"

    def _open_target_url(self, url: str):
        """Apre un URL secondo le impostazioni di configurazione."""
        cfg = ConfigManager()
        use_https = cfg.get_plugin_config(self.tag, "use_https", True)
        open_new = cfg.get_plugin_config(self.tag, "open_in_new_tab", False)
        
        if use_https and not url.startswith(("http://", "https://")):
            url = "https://" + url
        
        if open_new:
            webbrowser.open_new_tab(url)
        else:
            webbrowser.open(url)

    # --- METODI PUBBLICI (TOOLS) ---

    def open_url(self, url: str) -> str:
        """
        Opens a specific website in the default browser.
        
        :param url: The website address to open (e.g., 'youtube.com', 'wikipedia.org').
        """
        indirizzo = url.strip()
        logger.debug(f"PLUGIN_{self.tag}", f"Opening site: {indirizzo}")
        try:
            self._open_target_url(indirizzo)
            return translator.t("plugin_web_open_success", url=indirizzo)
        except Exception as e:
            logger.error(f"PLUGIN_{self.tag}: Error: {e}")
            return translator.t("plugin_web_error_network", error=str(e))

    def search_web(self, query: str) -> str:
        """
        Performs an internet search using the default search engine (e.g., Google).
        Automatically opens the browser with the search results.
        
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

# Istanzia pubblicamente lo strumento per l'esportazione verso il Core
tools = WebTools()

# --- COMPATIBILITY SHIMS ---
def info():
    return {"tag": tools.tag, "desc": tools.desc}

def status():
    return tools.status

def execute(comando: str) -> str:
    """Compatibilità legacy: smista i comandi testuali ai nuovi metodi ad oggetti."""
    c = comando.strip()
    c_lower = c.lower()
    
    if c_lower.startswith("search:") or c_lower.startswith("cerca:") or c_lower.startswith("search_web:"):
        q = c.split(":", 1)[1].strip()
        return tools.search_web(q)
    elif c_lower.startswith("url:") or c_lower.startswith("apri:") or c_lower.startswith("open_url:"):
        u = c.split(":", 1)[1].strip()
        return tools.open_url(u)
        
    return f"Errore: Comando legacy '{comando}' non supportato o mancante."