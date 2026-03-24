import json
import os
from core.logging import logger
from core.i18n import translator

def info():
    return {
        "tag": "MODELS",
        "desc": translator.t("plugin_models_desc"),
        "comandi": {
            "set:numero": translator.t("plugin_models_set_desc"),
            "lista": translator.t("plugin_models_lista_desc"),
            "backend": translator.t("plugin_models_backend_desc")
        }
    }

def status():
    return translator.t("plugin_models_status_online")

def esegui(comando):
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        cmd = comando.lower().strip()
        backend_type = config['backend']['tipo']
        backend_config = config['backend'][backend_type]
        
        if cmd == "backend":
            return f"Current backend: {backend_type.upper()}"
        
        if cmd == "lista":
            modelli = backend_config.get('modelli_disponibili', {})
            if not modelli:
                return f"No models configured for backend {backend_type}."
            result = f"Available models for {backend_type.upper()}:\n"
            for k, v in modelli.items():
                result += f"  [{k}] {v}\n"
            return result
        
        if cmd.startswith("set:"):
            import re
            numeri = re.findall(r'\d+', cmd)
            if not numeri:
                return "Error: Specify the model number (e.g. set:7)."
            
            indice = numeri[0]
            modelli = backend_config.get('modelli_disponibili', {})
            
            if indice in modelli:
                nuovo_modello = modelli[indice]
                # Aggiorna la configurazione
                config['backend'][backend_type]['modello'] = nuovo_modello
                
                with open('config.json', 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=4)
                
                return f"✅ Model set to: {nuovo_modello} (backend: {backend_type})"
            else:
                return f"Error: Model {indice} does not exist."
        
        return "Command not recognized. Use: set:number, list, backend"
        
    except Exception as e:
        logger.errore(f"MODELS: Error: {e}")
        return f"Critical error: {e}"