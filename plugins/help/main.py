from core.i18n import translator
from core.system import plugin_loader

def info():
    return {
        "tag": "HELP",
        "desc": translator.t("plugin_help_desc"),
        "comandi": {
            "lista": translator.t("plugin_help_cmd_lista"),
            "refresh": translator.t("plugin_help_cmd_refresh")
        },
        "esempio": "[HELP: lista]"
    }

def config_schema():
    return {
        "show_disabled": {
            "type": "bool",
            "default": False,
            "description": translator.t("plugin_help_show_disabled_desc")
        }
    }

def esegui(comando):
    cmd = comando.lower().strip()
    if cmd == "lista":
        return plugin_loader.ottieni_capacita_formattate()
    elif cmd == "refresh":
        plugin_loader.aggiorna_registro_capacita()
        return translator.t("plugin_help_refresh_success") + "\n" + plugin_loader.ottieni_capacita_formattate()
    else:
        return translator.t("plugin_help_cmd_unknown")