import webbrowser
import urllib.parse
from core.logging import logger
from app.config import ConfigManager

def info():
    """Manifest del plugin per il database centralizzato delle skills."""
    return {
        "tag": "WEB",
        "desc": "Accesso alla rete per ricerche Google e apertura rapida di siti web.",
        "comandi": {
            "search:query": "Esegue una ricerca su Google per il termine specificato.",
            "open:url": "Apre un indirizzo web nel browser predefinito."
        },
        "esempio": "[WEB: search: chi è Root Admin] oppure [WEB: open: youtube.com]"
    }

def status():
    """Stato del plugin."""
    return "ONLINE (Navigazione & Search)"

def config_schema():
    """
    Schema di configurazione per il plugin WEB.
    Permette di personalizzare motore di ricerca, protocollo e comportamento.
    """
    return {
        "search_engine": {
            "type": "str",
            "default": "google",
            "options": ["google", "duckduckgo", "bing"],
            "description": "Motore di ricerca predefinito (google, duckduckgo, bing)"
        },
        "use_https": {
            "type": "bool",
            "default": True,
            "description": "Forza HTTPS per le aperture di siti senza protocollo"
        },
        "open_in_new_tab": {
            "type": "bool",
            "default": False,
            "description": "Apre i link in una nuova scheda invece che in una nuova finestra"
        }
    }

def _get_search_url(query):
    """Restituisce l'URL di ricerca configurato."""
    cfg = ConfigManager()
    engine = cfg.get_plugin_config("WEB", "search_engine", "google")
    query_encoded = urllib.parse.quote(query)
    
    if engine == "google":
        return f"https://www.google.com/search?q={query_encoded}"
    elif engine == "duckduckgo":
        return f"https://duckduckgo.com/?q={query_encoded}"
    elif engine == "bing":
        return f"https://www.bing.com/search?q={query_encoded}"
    else:
        # fallback
        return f"https://www.google.com/search?q={query_encoded}"

def _open_url(url):
    """Apre un URL secondo le impostazioni di configurazione."""
    cfg = ConfigManager()
    use_https = cfg.get_plugin_config("WEB", "use_https", True)
    open_in_new_tab = cfg.get_plugin_config("WEB", "open_in_new_tab", False)
    
    if use_https and not url.startswith(("http://", "https://")):
        url = "https://" + url
    
    if open_in_new_tab:
        webbrowser.open_new_tab(url)
    else:
        webbrowser.open(url)

def esegui(comando):
    """Gestisce l'apertura di URL o ricerche con gestione dei prefissi."""
    cmd = comando.strip()
    logger.debug("PLUGIN_WEB", f"esegui() chiamato con comando: '{cmd}'")
    
    try:
        # 1. APERTURA SITI WEB
        if cmd.lower().startswith("open:"):
            url = cmd[5:].strip()
            _open_url(url)
            logger.debug("PLUGIN_WEB", f"Apertura sito: {url}")
            return f"Protocollo Web: Sito '{url}' aperto nel browser."

        # 2. RICERCA
        elif cmd.lower().startswith("search:"):
            query = cmd[7:].strip()
            url = _get_search_url(query)
            _open_url(url)
            logger.debug("PLUGIN_WEB", f"Ricerca: {query}")
            return f"Ricerca avviata: Ho cercato '{query}' per te, Admin."

        # 3. FALLBACK (Apertura generica se manca il prefisso)
        else:
            target = cmd
            _open_url(target)
            logger.debug("PLUGIN_WEB", f"Apertura generica: {target}")
            return f"Apertura generica tentata per: {target}"
            
    except Exception as e:
        logger.errore(f"PLUGIN_WEB: Errore: {e}")
        return f"Errore durante l'accesso alla rete: {str(e)}"