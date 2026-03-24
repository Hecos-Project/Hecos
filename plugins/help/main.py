try:
    from core.i18n import translator
    from core.system import plugin_loader
except ImportError:
    class DummyTranslator:
        def t(self, key, **kwargs): return key
    translator = DummyTranslator()
    class DummyLoader:
        def ottieni_capacita_formattate(self): return "Stand-alone mode: System capabilities not available."
        def aggiorna_registro_capacita(self): pass
    plugin_loader = DummyLoader()

class HelpTools:
    """
    Plugin: Help & Registry
    Strumenti per interrogare e aggiornare le capacità del sistema Zentra.
    """

    def __init__(self):
        self.tag = "HELP"
        self.desc = translator.t("plugin_help_desc")
        self.status = "ONLINE"
        
        self.config_schema = {
            "show_disabled": {
                "type": "bool",
                "default": False,
                "description": translator.t("plugin_help_show_disabled_desc")
            }
        }

    def list_capabilities(self) -> str:
        """
        Mostra la lista completa di tutti i tool, moduli e capacità attualmente caricati nel sistema.
        Usa questo comando per sapere cosa sei in grado di fare o per rispondere all'utente sulle tue funzioni.
        """
        return plugin_loader.ottieni_capacita_formattate()

    def refresh_registry(self) -> str:
        """
        Forza una rilettura e un aggiornamento del registro centrale delle capacità (ricansiona i plugin).
        Utile se un modulo è stato bloccato o aggiornato di recente.
        """
        plugin_loader.aggiorna_registro_capacita()
        return translator.t("plugin_help_refresh_success") + "\n" + plugin_loader.ottieni_capacita_formattate()

# Istanzia pubblicamente lo strumento per l'esportazione verso il Core
tools = HelpTools()

# --- COMPATIBILITY SHIMS ---
def info():
    return {"tag": tools.tag, "desc": tools.desc}

def status():
    return tools.status