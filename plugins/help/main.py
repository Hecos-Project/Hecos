from core.system import plugin_loader

def info():
    return {
        "tag": "HELP",
        "desc": "Visualizza l'elenco di tutti i comandi e moduli attivi nel sistema.",
        "comandi": {
            "lista": "Mostra tutti i protocolli disponibili.",
            "refresh": "Rigenera il registro dei plugin e mostra i comandi aggiornati."  # nuovo comando
        },
        "esempio": "[HELP: lista]"
    }

def config_schema():
    return {
        "show_disabled": {
            "type": "bool",
            "default": False,
            "description": "Mostra anche i plugin disabilitati nella guida"
        }
    }

def esegui(comando):
    cmd = comando.lower().strip()
    if cmd == "lista":
        # Usa la funzione corretta per ottenere la lista formattata
        return plugin_loader.ottieni_capacita_formattate()
    elif cmd == "refresh":
        plugin_loader.aggiorna_registro_capacita()
        return "✅ Registro capacità rigenerato.\n" + plugin_loader.ottieni_capacita_formattate()
    else:
        return "Comando sconosciuto. Usa 'lista' o 'refresh'."