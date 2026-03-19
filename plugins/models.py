import json
import os
from core import logger

def info():
    return {
        "tag": "MODELS",
        "desc": "Cambia il modello IA in base al backend attivo (Ollama/Kobold).",
        "comandi": {
            "set:numero": "Cambia il modello attivo usando il numero della lista (es: set:7).",
            "lista": "Mostra i modelli disponibili per il backend attuale.",
            "backend": "Mostra il backend attualmente in uso."
        }
    }

def status():
    return "ONLINE (Gestione modelli)"

def esegui(comando):
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        cmd = comando.lower().strip()
        backend_type = config['backend']['tipo']
        backend_config = config['backend'][backend_type]
        
        if cmd == "backend":
            return f"Backend attuale: {backend_type.upper()}"
        
        if cmd == "lista":
            modelli = backend_config.get('modelli_disponibili', {})
            if not modelli:
                return f"Nessun modello configurato per il backend {backend_type}."
            result = f"Modelli disponibili per {backend_type.upper()}:\n"
            for k, v in modelli.items():
                result += f"  [{k}] {v}\n"
            return result
        
        if cmd.startswith("set:"):
            import re
            numeri = re.findall(r'\d+', cmd)
            if not numeri:
                return "Errore: Specifica il numero del modello (es. set:7)."
            
            indice = numeri[0]
            modelli = backend_config.get('modelli_disponibili', {})
            
            if indice in modelli:
                nuovo_modello = modelli[indice]
                # Aggiorna la configurazione
                config['backend'][backend_type]['modello'] = nuovo_modello
                
                with open('config.json', 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=4)
                
                return f"✅ Modello impostato su: {nuovo_modello} (backend: {backend_type})"
            else:
                return f"Errore: Il modello {indice} non esiste."
        
        return "Comando non riconosciuto. Usa: set:numero, lista, backend"
        
    except Exception as e:
        logger.errore(f"MODELS: Errore: {e}")
        return f"Errore critico: {e}"