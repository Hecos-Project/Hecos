import os
import json
from hecos.core.logging import logger

class Translator:
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Translator, cls).__new__(cls)
        return cls._instance

    def __init__(self, language='en'):
        if hasattr(self, '_initialized') and self._initialized:
            # Allow updating language if explicitly passed during init
            if language != self.language:
                self.set_language(language)
            return
        self.language = language
        self.translations = {}
        self.base_translations = {}  # Fallback (en)
        self.locales_path = os.path.join(os.path.dirname(__file__), "locales")
        self._load_translations()
        self._initialized = True

    def _load_translations(self):
        """Loads JSON files for the selected language and the base one."""
        # Load base (en)
        en_path = os.path.join(self.locales_path, "en.json")
        if os.path.exists(en_path):
            with open(en_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.base_translations = data.get('en', {})

        # Load current language
        lang_path = os.path.join(self.locales_path, f"{self.language}.json")
        if os.path.exists(lang_path):
            with open(lang_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.translations = data.get(self.language, {})
        else:
            logger.warning("I18N", f"Language '{self.language}' not found; using fallback 'en'.")
            self.translations = self.base_translations

    def set_language(self, language):
        """Changes the language at runtime."""
        if self.language != language:
            self.language = language
            self._load_translations()

    def get_translations(self):
        """Returns the full dictionary for the current language."""
        return self.translations

    def t(self, key, **kwargs):
        """
        Retrieves the translated string and interpolates variables.
        Uses fallback to English if the key is missing in the current language.
        """
        text = self.translations.get(key)
        if text is None:
            text = self.base_translations.get(key, key) # Fallback to en, then to the key itself
            
        try:
            return text.format(**kwargs)
        except Exception as e:
            logger.error(f"I18N: Formatting error for '{key}': {e}")
            return text

# Global instance
_global_translator = None

def init_translator(language='en'):
    global _global_translator
    _global_translator = Translator(language)
    return _global_translator

def get_translator():
    global _global_translator
    if _global_translator is None:
        return init_translator()
    return _global_translator

def t(key, **kwargs):
    """Shorthand for translating."""
    return get_translator().t(key, **kwargs)
