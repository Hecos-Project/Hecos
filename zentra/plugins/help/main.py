try:
    from zentra.core.i18n import translator
    from zentra.core.system import plugin_loader
except ImportError:
    class DummyTranslator:
        def t(self, key, **kwargs): return key
    translator = DummyTranslator()
    class DummyLoader:
        def get_formatted_capabilities(self): return "Stand-alone mode: System capabilities not available."
        def update_capability_registry(self): pass
    plugin_loader = DummyLoader()

class HelpTools:
    """
    Plugin: Help & Registry
    Tools to query and update Zentra system capabilities.
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
        Displays the complete list of all tools, modules, and capabilities currently loaded in the system.
        Use this command to know what you are capable of or to answer the user about your functions.
        """
        return plugin_loader.get_formatted_capabilities()

    def refresh_registry(self) -> str:
        """
        Forces a re-read and update of the central capabilities registry (rescans plugins).
        Useful if a module has been locked or recently updated.
        """
        plugin_loader.update_capability_registry()
        return translator.t("plugin_help_refresh_success") + "\n" + plugin_loader.get_formatted_capabilities()

# Istanzia pubblicamente lo strumento per l'esportazione verso il Core
tools = HelpTools()

# --- COMPATIBILITY SHIMS ---
def info():
    return {"tag": tools.tag, "desc": tools.desc}

def status():
    return tools.status