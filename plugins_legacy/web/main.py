import webbrowser
import urllib.parse
from plugins_legacy.base import BaseLegacyPlugin

try:
    from core.logging import logger
    from core.i18n import translator
    from app.config import ConfigManager
except ImportError:
    pass

class WebLegacyPlugin(BaseLegacyPlugin):
    """
    Legacy Object-Oriented version of the WEB plugin.
    Allows small models to search the internet or open sites via simple tags:
    e.g. [WEB: search:today's weather] or [WEB: open:youtube.com]
    """
    def __init__(self):
        desc = translator.t("plugin_web_desc") if 'translator' in globals() else "Web Browsing"
        super().__init__("WEB", desc)
        
    def get_commands(self) -> dict:
        return {
            "search:<text>": "Search for something on the internet (e.g. search:Rome weather)",
            "open:<site>": "Open a specific website (e.g. open:wikipedia.org)"
        }
        
    # --- HELPERS ---
    def _get_search_url(self, query: str) -> str:
        engine = "google"
        if 'ConfigManager' in globals():
            cfg = ConfigManager()
            engine = cfg.get_plugin_config(self.tag, "search_engine", "google")
            
        query_encoded = urllib.parse.quote(query)
        if engine == "google":
            return f"https://www.google.com/search?q={query_encoded}"
        elif engine == "duckduckgo":
            return f"https://duckduckgo.com/?q={query_encoded}"
        elif engine == "bing":
            return f"https://www.bing.com/search?q={query_encoded}"
        return f"https://www.google.com/search?q={query_encoded}"

    def _open_target_url(self, url: str):
        use_https = True
        open_new = False
        if 'ConfigManager' in globals():
            cfg = ConfigManager()
            use_https = cfg.get_plugin_config(self.tag, "use_https", True)
            open_new = cfg.get_plugin_config(self.tag, "open_in_new_tab", False)
            
        if use_https and not url.startswith(("http://", "https://")):
            url = "https://" + url
            
        if open_new:
            webbrowser.open_new_tab(url)
        else:
            webbrowser.open(url)

    # --- CORE LOGIC ---
    def process_tag(self, command: str) -> str:
        command = command.strip()
        if 'logger' in globals():
            logger.debug("PLUGIN_WEB_LEGACY", f"Received command: {command}")
        
        if command.startswith("search:") or command.startswith("cerca:"):
            prefix = "search:" if command.startswith("search:") else "cerca:"
            ricerca = command[len(prefix):].strip()
            if not ricerca: return "No search query provided."
            try:
                url_ricerca = self._get_search_url(ricerca)
                self._open_target_url(url_ricerca)
                if 'translator' in globals():
                    return translator.t("plugin_web_search_success", query=ricerca)
                return f"Search for '{ricerca}' performed."
            except Exception as e:
                return f"Network error: {e}"
                
        elif command.startswith("open:") or command.startswith("apri:"):
            prefix = "open:" if command.startswith("open:") else "apri:"
            indirizzo = command[len(prefix):].strip()
            if not indirizzo: return "No website provided."
            try:
                self._open_target_url(indirizzo)
                if 'translator' in globals():
                    return translator.t("plugin_web_open_success", url=indirizzo)
                return f"Site {indirizzo} opened."
            except Exception as e:
                return f"Error: {e}"
                
        return f"Invalid tag syntax for WEB command: {command}"

def get_plugin():
    return WebLegacyPlugin()
