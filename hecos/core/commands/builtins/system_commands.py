"""
HDCS — Builtin System Commands
Core commands that don't require plugins: /help, /status, /clear, /config
"""

import logging

_log = logging.getLogger("HecosSystemCommands")


# ── Handlers ──────────────────────────────────────────────────────────────────

def _cmd_help(raw_args_str="", config=None, config_manager=None, **kwargs) -> str:
    """Return a formatted list of all available commands."""
    from hecos.core.commands.registry import get_registry
    registry = get_registry(config=config)
    cmds = sorted(registry.get_all(), key=lambda c: (c["category"], c["id"]))

    lines = ["## ⚡ Hecos Direct Commands\n"]
    current_cat = None
    for cmd in cmds:
        cat = cmd["category"]
        if cat != current_cat:
            current_cat = cat
            lines.append(f"\n### {cat}")
        icon = cmd.get("icon", "•")
        alias = cmd["aliases"][0]
        desc = cmd["description"]
        lines.append(f"- {icon} `{alias}` — {desc}")

    lines.append("\n---")
    lines.append("*Digita `/` nella chat e usa la palette per cercare e autocomplete.*")
    return "\n".join(lines)


def _cmd_status(raw_args_str="", config=None, config_manager=None, **kwargs) -> str:
    """Return a system status summary."""
    cfg = config or (config_manager.config if config_manager else {})
    lines = ["## 🖥️ Hecos System Status\n"]

    # Model info
    try:
        model = cfg.get("ai", {}).get("model", "Unknown")
        provider = cfg.get("ai", {}).get("provider", "Unknown")
        lines.append(f"**Modello:** `{model}` via `{provider}`")
    except Exception:
        lines.append("**Modello:** N/A")

    # Plugin count
    try:
        from hecos.core.system.module_state import _loaded_plugins, _lazy_plugins_paths
        total = len(_loaded_plugins) + len(_lazy_plugins_paths)
        lines.append(f"**Plugin attivi:** {total} ({len(_loaded_plugins)} eager + {len(_lazy_plugins_paths)} lazy)")
    except Exception:
        lines.append("**Plugin:** N/A")

    # Command count
    try:
        from hecos.core.commands.registry import get_registry
        n = len(get_registry(config=cfg).get_all())
        lines.append(f"**Comandi slash:** {n}")
    except Exception:
        pass

    # Memory
    try:
        import psutil
        mem = psutil.virtual_memory()
        lines.append(f"**RAM:** {mem.percent:.1f}% usata ({mem.available // 1024 // 1024} MB liberi)")
    except Exception:
        pass

    # Version
    try:
        from hecos.core.system.version import VERSION
        lines.append(f"**Versione Hecos:** `{VERSION}`")
    except Exception:
        pass

    return "\n".join(lines)


def _cmd_clear(raw_args_str="", config=None, current_user_id="admin", session_id=None, **kwargs) -> str:
    """Clear conversation history for the current session."""
    try:
        from hecos.memory import brain_interface
        brain_interface.clear_history(user_id=current_user_id, session_id=session_id)
        return "✅ Cronologia conversazione cancellata."
    except Exception as e:
        return f"❌ Errore durante la cancellazione: {e}"


def _cmd_config_get(raw_args_str="", config=None, config_manager=None, **kwargs) -> str:
    """Read a configuration value by dot-notation key."""
    if not raw_args_str.strip():
        return "**Uso:** `/config get <chiave>` — es. `/config get ai.model`"
    cfg = config or (config_manager.config if config_manager else {})
    key_path = raw_args_str.strip().split(".")
    val = cfg
    try:
        for k in key_path:
            val = val[k]
        return f"**`{raw_args_str}`** = `{val}`"
    except (KeyError, TypeError):
        return f"❌ Chiave non trovata: `{raw_args_str}`"


def _cmd_config_set(raw_args_str="", config=None, config_manager=None, **kwargs) -> str:
    """Set a configuration value (runtime only unless saved)."""
    parts = raw_args_str.strip().split(" ", 1)
    if len(parts) < 2:
        return "**Uso:** `/config set <chiave> <valore>` — es. `/config set ai.model gemini/gemini-2.0-flash`"
    key_dotted, value = parts[0], parts[1]
    if not config_manager:
        return "❌ ConfigManager non disponibile in questo contesto."
    try:
        key_parts = key_dotted.split(".")
        config_manager.set(value, *key_parts)
        return f"✅ Impostato `{key_dotted}` = `{value}` *(solo RAM — usa Central Hub per salvare)*"
    except Exception as e:
        return f"❌ Impossibile impostare `{key_dotted}`: {e}"


def _cmd_reload_commands(raw_args_str="", config=None, **kwargs) -> str:
    """Force a reload of the command registry (useful after loading new plugins)."""
    try:
        from hecos.core.commands.registry import get_registry
        registry = get_registry(config=config, reload=True)
        return f"✅ Registry ricaricato: {len(registry.get_all())} comandi disponibili."
    except Exception as e:
        return f"❌ Errore reload registry: {e}"


def _cmd_souls(raw_args_str="", config=None, config_manager=None, **kwargs) -> str:
    """List all available AI personalities (souls)."""
    try:
        from hecos.modules.personality.main import tools as personality_tools
        return personality_tools.list_souls(config_manager=config_manager)
    except Exception as e:
        # Fallback: scan the personality directory directly
        try:
            import os
            hecos_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
            p_dir = os.path.join(hecos_dir, "personality")
            files = sorted([f for f in os.listdir(p_dir) if f.endswith('.yaml')])
            if not files:
                return "❌ Nessuna personalità trovata."
            cfg = config or (config_manager.config if config_manager else {})
            active = cfg.get("ai", {}).get("active_personality", "")
            lines = ["## 🧠 Personalità Disponibili\n"]
            for i, f in enumerate(files):
                name = f.replace('.yaml', '')
                marker = " ✦ *attiva*" if f == active else ""
                lines.append(f"{i+1}. **{name}**{marker}")
            lines.append("\n*Usa `/soul <nome>` per cambiare.*")
            return "\n".join(lines)
        except Exception as e2:
            return f"❌ Errore: {e2}"


def _cmd_soul(raw_args_str="", config=None, config_manager=None, **kwargs) -> str:
    """Switch the active AI personality by name or index number."""
    name = raw_args_str.strip()
    if not name:
        return "**Uso:** `/soul <nome_o_indice>` — es. `/soul Motoko` oppure `/soul 2`\n\nUsa `/souls` per vedere la lista completa."
    try:
        from hecos.modules.personality.main import tools as personality_tools
        return personality_tools.switch_soul(name, config_manager=config_manager)
    except Exception as e:
        return f"❌ Errore durante il cambio personalità: {e}"


# ── Command descriptors ───────────────────────────────────────────────────────



def _cmd_info(raw_args_str: str = "", config=None, config_manager=None, **kwargs) -> str:
    """Show the capability card for a named Hecos module/package."""
    plugin_id = raw_args_str.strip().lower()
    if not plugin_id:
        return (
            "**Usage:** `/info <module_id>`\n"
            "**Example:** `/info webcam`\n\n"
            "Shows the capability profile of an installed Hecos module."
        )

    try:
        from hecos.core.system.capability_inspector import build_card

        # Check if auto-introspect is enabled in config
        cfg = config or (config_manager.config if config_manager else {})
        introspect = (
            cfg.get("hpm", {}).get("auto_introspect", False)
            if isinstance(cfg, dict) else False
        )

        card = build_card(plugin_id, introspect=introspect)
        if card is None:
            return (
                f"❌ Module **{plugin_id}** not found or not installed.\n"
                f"Use `/modules` to list all installed modules."
            )
        return "```\n" + card.format_card() + "\n```"
    except Exception as e:
        import logging
        logging.getLogger("HecosSystemCommands").error(f"[/info] Error building card for '{plugin_id}': {e}")
        return f"❌ Error retrieving info for **{plugin_id}**: {e}"

SYSTEM_COMMANDS = [
    {
        "id": "help",
        "aliases": ["/help", "/?", "/comandi"],
        "description": "Mostra tutti i comandi slash disponibili",
        "usage": "/help",
        "example": "/help",
        "icon": "📋",
        "category": "CORE",
        "requires_auth": "any",
        "requires_args": False,
        "save_to_memory": False,
        "_handler": _cmd_help,
    },
    {
        "id": "status",
        "aliases": ["/status", "/info"],
        "description": "Mostra lo stato del sistema (modello, plugin, RAM)",
        "usage": "/status",
        "example": "/status",
        "icon": "🖥️",
        "category": "CORE",
        "requires_auth": "any",
        "requires_args": False,
        "save_to_memory": False,
        "_handler": _cmd_status,
    },
    {
        "id": "clear",
        "aliases": ["/clear", "/pulisci", "/reset"],
        "description": "Cancella la cronologia della conversazione corrente",
        "usage": "/clear",
        "example": "/clear",
        "icon": "🗑️",
        "category": "CORE",
        "requires_auth": "any",
        "requires_args": False,
        "save_to_memory": False,
        "_handler": _cmd_clear,
    },
    {
        "id": "config_get",
        "aliases": ["/config get"],
        "description": "Legge un valore di configurazione (dot-notation)",
        "usage": "/config get <chiave>",
        "example": "/config get ai.model",
        "icon": "🔍",
        "category": "CORE",
        "requires_auth": "admin",
        "requires_args": True,
        "_handler": _cmd_config_get,
    },
    {
        "id": "config_set",
        "aliases": ["/config set"],
        "description": "Imposta un valore di configurazione (solo RAM)",
        "usage": "/config set <chiave> <valore>",
        "example": "/config set ai.model gemini/gemini-2.0-flash",
        "icon": "⚙️",
        "category": "CORE",
        "requires_auth": "admin",
        "requires_args": True,
        "_handler": _cmd_config_set,
    },
    {
        "id": "reload",
        "aliases": ["/reload", "/reload_commands"],
        "description": "Ricarica il registro dei comandi slash",
        "usage": "/reload",
        "example": "/reload",
        "icon": "🔄",
        "category": "CORE",
        "requires_auth": "admin",
        "requires_args": False,
        "save_to_memory": False,
        "_handler": _cmd_reload_commands,
    },
    {
        "id": "souls",
        "aliases": ["/souls", "/personas", "/personality list"],
        "description": "Elenca tutte le personalità (Souls) disponibili",
        "usage": "/souls",
        "example": "/souls",
        "icon": "📋",
        "category": "PERSONA",
        "requires_auth": "any",
        "requires_args": False,
        "save_to_memory": False,
        "_handler": _cmd_souls,
    },
    {
        "id": "soul",
        "aliases": ["/soul", "/persona", "/switch soul"],
        "description": "Cambia la personalità attiva (per nome o numero)",
        "usage": "/soul <nome_o_indice>",
        "example": "/soul Motoko",
        "icon": "🧠",
        "category": "PERSONA",
        "requires_auth": "any",
        "requires_args": True,
        "save_to_memory": False,
        "_handler": _cmd_soul,
    },
    {
        "id": "info",
        "aliases": ["/info", "/module info", "/pkg info"],
        "description": "Shows the capability card for a Hecos module or package",
        "usage": "/info <module_id>",
        "example": "/info webcam",
        "icon": "🧩",
        "category": "CORE",
        "requires_auth": "any",
        "requires_args": True,
        "save_to_memory": False,
        "_handler": _cmd_info,
    },
]
