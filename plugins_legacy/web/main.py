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
    Versione Legacy a Oggetti del plugin WEB.
    Permette ai modelli piccoli di cercare su internet o aprire siti tramite semplici tag:
    es. [WEB: cerca:meteo di oggi] oppure [WEB: apri:youtube.com]
    """
    def __init__(self):
        desc = translator.t("plugin_web_desc") if 'translator' in globals() else "Web Browsing"
        super().__init__("WEB", desc)
        
    def ottieni_comandi(self) -> dict:
        return {
            "cerca:<testo>": "Cerca qualcosa su internet (es. cerca:meteo Roma)",
            "apri:<sito>": "Apre un sito web specifico (es. apri:wikipedia.org)"
        }
        
    # --- HELPER (Presi dal modulo Nativo) ---
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
    def elabora_tag(self, comando: str) -> str:
        comando = comando.strip()
        if 'logger' in globals():
            logger.debug("PLUGIN_WEB_LEGACY", f"Ricevuto comando: {comando}")
        
        if comando.startswith("cerca:"):
            ricerca = comando[6:].strip()
            if not ricerca: return "Nessun testo di ricerca fornito."
            try:
                url_ricerca = self._get_search_url(ricerca)
                self._open_target_url(url_ricerca)
                if 'translator' in globals():
                    return translator.t("plugin_web_search_success", query=ricerca)
                return f"Ricerca per '{ricerca}' effettuata."
            except Exception as e:
                return f"Errore di rete: {e}"
                
        elif comando.startswith("apri:"):
            indirizzo = comando[5:].strip()
            if not indirizzo: return "Nessun sito fornito."
            try:
                self._open_target_url(indirizzo)
                if 'translator' in globals():
                    return translator.t("plugin_web_open_success", url=indirizzo)
                return f"Sito {indirizzo} aperto."
            except Exception as e:
                return f"Errore: {e}"
                
        return f"Sintassi tag non valida per il comando WEB: {comando}"

def get_plugin():
    return WebLegacyPlugin()
