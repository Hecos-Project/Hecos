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

    def reload_config(self):
        """Forza la ricarica manuale della configurazione per applicare le modifiche fatte dal pannello F7."""
        self._load_config()

    def get_model_for_tag(self, tag: str, config_override: dict = None) -> str:
        """
        Restituisce il modello configurato per un determinato tag (es. 'ROLEPLAY', 'WEB').
        Se non specificato o vuoto, restituisce None (per usare il default globale).
        """
        cfg = config_override if config_override is not None else self._config
        if not cfg:
            return None

        # Ricerca nei plugin
        plugins = cfg.get("plugins", {})
        if tag in plugins:
            model = plugins[tag].get("modello_llm")
            if model:
                # Check se il modello è cloud e il cloud è disattivato globalmente
                allow_cloud = cfg.get("llm", {}).get("allow_cloud", False)
                is_cloud = any(model.startswith(p + "/") for p in ["groq", "openai", "anthropic", "gemini", "cohere"])
                if is_cloud and not allow_cloud:
                    return None # Forza fallback ignorando l'override del plugin
                return model

        # Possibilità futura: ricerca in core_features
        # core_features = cfg.get("core_features", {})
        # if tag in core_features:
        #     return core_features[tag].get("modello_llm")

        return None

    def get_default_model(self, config_override: dict = None) -> str:
        """Restituisce il modello predefinito globale configurato nel backend attivo."""
        cfg = config_override if config_override is not None else self._config
        if not cfg:
            return ""
        
        from app.model_manager import ModelManager
        _, modello = ModelManager.get_effective_model_info(cfg)
        return modello

    def resolve_model(self, tag: str = None, config_override: dict = None) -> str:
        """Risolve quale modello usare: quello specifico del tag o quello di default."""
        if tag:
            specific_model = self.get_model_for_tag(tag, config_override=config_override)
            if specific_model:
                return specific_model
        
        return self.get_default_model(config_override=config_override)

# Istanza singleton facile da importare
manager = LLMManager()
