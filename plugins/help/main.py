from core import plugin_loader

def info():
    return {
        "tag": "HELP",
        "desc": "Visualizza l'elenco di tutti i comandi e moduli attivi nel sistema.",
        "comandi": {
            "lista": "Mostra tutti i protocolli disponibili."
        },
        "esempio": "[HELP: lista]"
    }

def esegui(comando):
    # Richiama il loader per avere i dati freschi
    return plugin_loader.ottieni_capacita_plugins()