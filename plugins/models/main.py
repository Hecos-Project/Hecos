import json
import os
import re
try:
    from core.logging import logger
    from core.i18n import translator
except ImportError:
    class DummyLogger:
        def debug(self, *args, **kwargs): print("[MOD_DEBUG]", *args)
        def errore(self, *args, **kwargs): print("[MOD_ERR]", *args)
    logger = DummyLogger()
    class DummyTranslator:
        def t(self, key, **kwargs): return key
    translator = DummyTranslator()

class ModelsTools:
    """
    Plugin: Models & Backend Manager
    Permette di gestire i modelli LLM e visualizzare lo stato del backend.
    """

    def __init__(self):
        self.tag = "MODELS"
        self.desc = translator.t("plugin_models_desc")
        self.status = translator.t("plugin_models_status_online")

    def get_current_backend(self) -> str:
        """
        Restituisce il backend AI correntemente in uso (es. cloud, ollama, kobold).
        """
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
            backend_type = config['backend']['tipo']
            return f"Current backend: {backend_type.upper()}"
        except Exception as e:
            logger.errore(f"MODELS: Error: {e}")
            return f"Critical error: {e}"

    def list_models(self) -> str:
        """
        Elenca tutti i modelli disponibili per il backend attualmente selezionato.
        Tenta di recuperare la lista aggiornata via API (Ollama, Groq, OpenAI).
        """
        try:
            from app.config import ConfigManager
            from app.model_manager import ModelManager
            import requests

            cfg_manager = ConfigManager()
            model_mgr = ModelManager(cfg_manager)
            
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            backend_attuale = config.get('backend', {}).get('tipo', 'ollama')
            all_models = []
            
            # Ollama (Local)
            try:
                response = requests.get("http://localhost:11434/api/tags", timeout=1)
                if response.status_code == 200:
                    for m in response.json().get('models', []):
                        if backend_attuale == "ollama":
                            all_models.append(m['name'])
            except: pass
            
            # Cloud
            if backend_attuale == "cloud":
                providers = config.get('llm', {}).get('providers', {})
                for p_name, p_data in providers.items():
                    api_key = p_data.get('api_key') or os.environ.get(f"{p_name.upper()}_API_KEY")
                    if api_key and p_name in ["groq", "openai"]:
                        cloud_m = model_mgr._fetch_cloud_models(p_name, api_key)
                        for m_name in cloud_m:
                            full_name = f"{p_name}/{m_name}" if not m_name.startswith(f"{p_name}/") else m_name
                            all_models.append(full_name)

            if not all_models:
                backend_config = config['backend'].get(backend_attuale, {})
                modelli_dict = backend_config.get('modelli_disponibili', {})
                all_models = list(modelli_dict.values())

            if not all_models:
                return f"Nessun modello trovato per il backend {backend_attuale}."

            self.last_listed_models = all_models
            result = f"Modelli disponibili ({backend_attuale.upper()}):\n"
            for i, m in enumerate(all_models, 1):
                result += f"  [{i}] {m}\n"
            return result
        except Exception as e:
            return f"Error: {e}"

    def set_model(self, model_number: str) -> str:
        """
        Imposta un nuovo modello AI attivo in base all'indice numerico ricavato da list_models.
        """
        try:
            numeri = re.findall(r'\d+', str(model_number))
            if not numeri:
                return "Error: Specificare il numero (es. 1)."
            
            idx = int(numeri[0]) - 1
            if hasattr(self, 'last_listed_models') and 0 <= idx < len(self.last_listed_models):
                nuovo_modello = self.last_listed_models[idx]
                with open('config.json', 'r', encoding='utf-8') as f:
                    config = json.load(f)
                b_type = config['backend']['tipo']
                config['backend'][b_type]['modello'] = nuovo_modello
                with open('config.json', 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=4)
                return f"✅ Modello impostato correttamente: {nuovo_modello}"
            return "Errore: Indice non valido o lista non caricata."
        except Exception as e:
            return f"Error: {e}"

# Istanzia pubblicamente lo strumento per l'esportazione verso il Core
tools = ModelsTools()

# --- COMPATIBILITY SHIMS ---
def info():
    return {"tag": tools.tag, "desc": tools.desc}

def status():
    return tools.status
