import os
import json
from core.logging import logger

class Translator:
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Translator, cls).__new__(cls)
        return cls._instance

    def __init__(self, lingua='it'):
        if hasattr(self, '_initialized') and self._initialized:
            return
        self.lingua = lingua
        self.translations = {}
        self.base_translations = {}  # Fallback (en)
        self.locales_path = os.path.join(os.path.dirname(__file__), "locales")
        self._load_translations()
        self._initialized = True

    def _load_translations(self):
        """Carica i file JSON per la lingua selezionata e quella base."""
        # Carica base (en)
        en_path = os.path.join(self.locales_path, "en.json")
        if os.path.exists(en_path):
            with open(en_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.base_translations = data.get('en', {})

        # Carica lingua attuale
        lang_path = os.path.join(self.locales_path, f"{self.lingua}.json")
        if os.path.exists(lang_path):
            with open(lang_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.translations = data.get(self.lingua, {})
        else:
            logger.warning("I18N", f"Language '{self.lingua}' not found; using fallback 'en'.")
            self.translations = self.base_translations

    def set_language(self, lingua):
        """Cambia la lingua a runtime."""
        if self.lingua != lingua:
            self.lingua = lingua
            self._load_translations()

    def t(self, key, **kwargs):
        """
        Recupera la stringa tradotta e interpola le variabili.
        Usa fallback su inglese se la chiave manca nella lingua attuale.
        """
        text = self.translations.get(key)
        if text is None:
            text = self.base_translations.get(key, key) # Fallback su en, poi sulla chiave stessa
            
        try:
            return text.format(**kwargs)
        except Exception as e:
            logger.errore(f"I18N: Formatting error for '{key}': {e}")
            return text

# Istanza globale
_global_translator = None

def init_translator(lingua='it'):
    global _global_translator
    _global_translator = Translator(lingua)
    return _global_translator

def get_translator():
    global _global_translator
    if _global_translator is None:
        return init_translator()
    return _global_translator

def t(key, **kwargs):
    """Shorthand per tradurre."""
    return get_translator().t(key, **kwargs)
