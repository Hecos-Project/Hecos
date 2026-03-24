import json
import os

class LLMManager:
    """
    Gestore dinamico per lo smistamento delle richieste LLM.
    Permette di definire modelli specifici per ogni plugin o funzionalità.
    """
    _instance = None
    _config = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LLMManager, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        config_path = "config.json"
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    self._config = json.load(f)
            except Exception as e:
                print(f"[LLMManager] Config load error: {e}")
                self._config = {}
        else:
            self._config = {}

    def get_model_for_tag(self, tag: str) -> str:
        """
        Restituisce il modello configurato per un determinato tag (es. 'ROLEPLAY', 'WEB').
        Se non specificato o vuoto, restituisce None (per usare il default globale).
        """
        if not self._config:
            return None

        # Ricerca nei plugin
        plugins = self._config.get("plugins", {})
        if tag in plugins:
            model = plugins[tag].get("modello_llm")
            if model:
                return model

        # Possibilità futura: ricerca in core_features
        # core_features = self._config.get("core_features", {})
        # if tag in core_features:
        #     return core_features[tag].get("modello_llm")

        return None

    def get_default_model(self) -> str:
        """Restituisce il modello predefinito globale configurato nel backend attivo."""
        if not self._config:
            return ""
        
        backend_tipo = self._config.get("backend", {}).get("tipo", "ollama")
        if backend_tipo == "cloud":
            return self._config.get("backend", {}).get("cloud", {}).get("modello", "")
        elif backend_tipo == "ollama":
            return self._config.get("backend", {}).get("ollama", {}).get("modello", "")
        elif backend_tipo == "kobold":
            return self._config.get("backend", {}).get("kobold", {}).get("modello", "")
        
        return ""

    def resolve_model(self, tag: str = None) -> str:
        """Risolve quale modello usare: quello specifico del tag o quello di default."""
        if tag:
            specific_model = self.get_model_for_tag(tag)
            if specific_model:
                return specific_model
        
        return self.get_default_model()

# Istanza singleton facile da importare
manager = LLMManager()
