import webbrowser
import urllib.parse

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
    return "ONLINE (Navigazione & Search)"

def esegui(comando):
    """Gestisce l'apertura di URL o ricerche con gestione dei prefissi."""
    cmd = comando.strip()
    
    try:
        # 1. APERTURA SITI WEB
        if cmd.lower().startswith("open:"):
            url = cmd[5:].strip()
            # Validazione protocollo
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            webbrowser.open(url)
            return f"Protocollo Web: Sito '{url}' aperto nel browser."

        # 2. RICERCA GOOGLE
        elif cmd.lower().startswith("search:"):
            query = cmd[7:].strip()
            query_encoded = urllib.parse.quote(query)
            url = f"https://www.google.com/search?q={query_encoded}"
            webbrowser.open(url)
            return f"Ricerca avviata: Ho cercato '{query}' per te, Admin."

        # 3. FALLBACK (Apertura generica se manca il prefisso)
        else:
            target = cmd
            if not target.startswith(("http://", "https://")):
                target = "https://" + target
            webbrowser.open(target)
            return f"Apertura generica tentata per: {target}"
            
    except Exception as e:
        return f"Errore durante l'accesso alla rete: {str(e)}"