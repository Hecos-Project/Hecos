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


def _cmd_author(raw_args_str="", **kwargs) -> str:
    """Return the authorship and copyright card."""
    try:
        from hecos.core.identity import get_author_card
        return get_author_card(include_address=False)
    except ImportError:
        return "⚠️ Hecos identity module missing or tampered with."
    except Exception as e:
        return f"❌ Error retrieving authorship info: {e}"


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


def _cmd_show(raw_args_str="", **kwargs) -> str:
    """
    Show a local file as a rich card in chat (with Visual Editor button for HTML files).
    Usage: /show <percorso_file>  or  /show docs  (to list all documents)
    """
    import os
    path = raw_args_str.strip().strip('"').strip("'")
    
    if not path:
        return (
            "**Uso:** `/show <percorso o nome file>`\n"
            "Esempi:\n"
            "- `/show C:\\Hecos\\hecos\\media\\documents\\mio_doc.html`\n"
            "- `/show mio_doc.html` (cerca in media/documents)\n"
            "- `/docs` per vedere tutti i documenti disponibili"
        )
    
    # If not an absolute path, look in media/documents
    if not os.path.isabs(path):
        hecos_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        docs_dir = os.path.join(hecos_dir, "media", "documents")
        candidates = [path, path + ".html", path + ".pdf"]
        resolved = None
        for c in candidates:
            full = os.path.join(docs_dir, c)
            if os.path.exists(full):
                resolved = full
                break
        # Fuzzy search
        if not resolved and os.path.isdir(docs_dir):
            for f in os.listdir(docs_dir):
                if path.lower() in f.lower():
                    resolved = os.path.join(docs_dir, f)
                    break
        if not resolved:
            return f"❌ File non trovato: `{path}`. Prova con il percorso completo."
        path = resolved
    elif not os.path.exists(path):
        return f"❌ File non trovato: `{path}`"
    import urllib.parse
    fname = os.path.basename(path)
    url_path = path.replace('\\', '/')
    safe_path = urllib.parse.quote(url_path)
    return f"[{fname}](/api/local_file?path={safe_path})\n*{path}*"


def _cmd_docs_list(raw_args_str="", **kwargs) -> str:
    """Elenco di tutti i documenti in media/documents con link cliccabili."""
    import os, re
    hecos_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    docs_dir = os.path.join(hecos_dir, "media", "documents")
    
    if not os.path.isdir(docs_dir):
        return f"❌ Cartella documenti non trovata: `{docs_dir}`"
    
    search = raw_args_str.strip().lower()
    files = sorted([
        f for f in os.listdir(docs_dir)
        if os.path.isfile(os.path.join(docs_dir, f))
        and (not search or search in f.lower())
    ])
    
    if not files:
        return "📂 Nessun documento trovato" + (f" per '{search}'" if search else "") + f" in `{docs_dir}`"
    
    import urllib.parse
    lines = [f"## 📁 Documenti ({len(files)} file)\n"]
    for f in files:
        full_path = os.path.join(docs_dir, f)
        url_path = full_path.replace('\\', '/')
        safe_path = urllib.parse.quote(url_path)
        size_bytes = os.path.getsize(full_path)
        size_str = f"{size_bytes/1024:.1f} KB" if size_bytes > 1024 else f"{size_bytes} B"
        
        # For HTML files, include image count
        extra = ""
        if f.endswith(".html"):
            try:
                with open(full_path, "r", encoding="utf-8", errors="replace") as fh:
                    html = fh.read()
                img_count = len(re.findall(r'<img\s', html, re.IGNORECASE))
                extra = f" — {img_count} immagini"
            except Exception:
                pass
        
        lines.append(f"[{f}](/api/local_file?path={safe_path}) ({size_str}){extra}")
    
    lines.append("\n*Clicca su un file per aprirlo o modificarlo.*")
    return "\n".join(lines)


def _cmd_souls(raw_args_str="", config=None, config_manager=None, **kwargs) -> str:
    """List all available AI personalities (souls)."""
    try:
        from hecos.modules.personality.main import tools as personality_tools
        return personality_tools.list_souls(config_manager=config_manager)
    except Exception as e:
        # Fallback: scan the personas directory directly
        try:
            import os
            hecos_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
            p_dir = os.path.join(hecos_dir, "personas")
            files = sorted([d for d in os.listdir(p_dir) if os.path.isdir(os.path.join(p_dir, d))])
            if not files:
                return "❌ Nessuna personalità trovata."
            cfg = config or (config_manager.config if config_manager else {})
            active = cfg.get("ai", {}).get("active_personality", "").replace(".yaml", "")
            lines = ["## 🧠 Personalità Disponibili\n"]
            for i, name in enumerate(files):
                marker = " ✦ *attiva*" if name == active else ""
                lines.append(f"{i+1}. **{name}**{marker}")
            lines.append("\n*Usa `/soul <nome>` per cambiare.*")
            return "\n".join(lines)
        except Exception as e2:
            return f"❌ Errore: {e2}"


def _cmd_tools(raw_args_str="", config=None, session_id=None, **kwargs) -> str:
    """Toggle or show function calling tools payload status."""
    from hecos.memory.session_config_db import get_session_config, set_session_config
    arg = raw_args_str.strip().lower()

    sid = session_id
    if not sid:
        try:
            from hecos.memory.session_crud import get_sessions
            sessions = get_sessions()
            if sessions:
                sid = sessions[0].get("id")
        except Exception:
            sid = "default"

    ov = get_session_config(sid) if sid else {}
    if "payload_control" not in ov:
        ov["payload_control"] = {}

    current_state = ov["payload_control"].get("send_tools")
    if current_state is None:
        if isinstance(config, dict) and "payload_control" in config:
            current_state = config["payload_control"].get("send_tools", True)
        else:
            current_state = True

    if arg in ("off", "disattiva", "disabilita", "disabilitato", "disable", "false", "0", "no"):
        new_state = False
    elif arg in ("on", "attiva", "abilita", "abilitato", "enable", "true", "1", "si", "yes"):
        new_state = True
    elif not arg:
        new_state = not current_state
    else:
        return f"⚠️ **Uso:** `/tools on` oppure `/tools off` (oppure comando rapido `/notools`)"

    ov["payload_control"]["send_tools"] = new_state
    if sid:
        set_session_config(sid, ov)
    if isinstance(config, dict):
        config.setdefault("payload_control", {})["send_tools"] = new_state

    status_str = "🟢 **ENABLED**" if new_state else "🔴 **DISABLED**"
    tip = (
        "Function JSON schemas (~85KB / ~25k tokens) **will be sent** to the model."
        if new_state
        else "No tool JSON schemas will be sent to the model. **Maximum inference speed and zero token overhead**."
    )
    return f"🔧 **Function Calling Tools**: {status_str}\n\n{tip}\n\n*Use `/payload` to inspect current payload metrics or `/tools` to toggle.*"


def _cmd_notools(raw_args_str="", **kwargs) -> str:
    """Direct shortcut to disable tools."""
    return _cmd_tools("off", **kwargs)


def _cmd_sendtools(raw_args_str="", **kwargs) -> str:
    """Direct shortcut to enable tools."""
    return _cmd_tools("on", **kwargs)


def _cmd_memory(raw_args_str="", config=None, session_id=None, **kwargs) -> str:
    """Toggle or show memory & chat history payload status."""
    from hecos.memory.session_config_db import get_session_config, set_session_config
    arg = raw_args_str.strip().lower()

    sid = session_id
    if not sid:
        try:
            from hecos.memory.session_crud import get_sessions
            sessions = get_sessions()
            if sessions:
                sid = sessions[0].get("id")
        except Exception:
            sid = "default"

    ov = get_session_config(sid) if sid else {}
    if "payload_control" not in ov:
        ov["payload_control"] = {}

    current_state = ov["payload_control"].get("send_memory")
    if current_state is None:
        if isinstance(config, dict) and "payload_control" in config:
            current_state = config["payload_control"].get("send_memory", True)
        else:
            current_state = True

    if arg in ("off", "disattiva", "disabilita", "disabilitato", "disable", "false", "0", "no"):
        new_state = False
    elif arg in ("on", "attiva", "abilita", "abilitato", "enable", "true", "1", "si", "yes"):
        new_state = True
    elif not arg:
        new_state = not current_state
    else:
        return f"⚠️ **Uso:** `/memory on` oppure `/memory off` (oppure comando rapido `/nomemory`)"

    ov["payload_control"]["send_memory"] = new_state
    if sid:
        set_session_config(sid, ov)
    if isinstance(config, dict):
        config.setdefault("payload_control", {})["send_memory"] = new_state

    status_str = "🟢 **ENABLED**" if new_state else "🔴 **DISABLED**"
    tip = (
        "Chat conversation history and memory recalls **will be included** in the prompt."
        if new_state
        else "No past chat history or memory vault blocks will be sent. The model will respond in zero-shot mode."
    )
    return f"🧠 **Memory & History**: {status_str}\n\n{tip}\n\n*Use `/payload` to inspect current payload metrics or `/memory` to toggle.*"


def _cmd_nomemory(raw_args_str="", **kwargs) -> str:
    """Direct shortcut to disable memory."""
    return _cmd_memory("off", **kwargs)


def _cmd_soul(raw_args_str="", config=None, config_manager=None, session_id=None, **kwargs) -> str:
    """Switch the active AI personality or toggle personality directives (Pure LLM)."""
    name = raw_args_str.strip()
    name_lower = name.lower()

    if name_lower in ("off", "disable", "disattiva", "disabilita", "raw", "pure", "false", "0", "no"):
        from hecos.memory.session_config_db import get_session_config, set_session_config
        sid = session_id
        if not sid:
            try:
                from hecos.memory.session_crud import get_sessions
                s = get_sessions()
                if s: sid = s[0].get("id")
            except Exception:
                sid = "default"
        ov = get_session_config(sid) if sid else {}
        ov.setdefault("payload_control", {})["send_personality"] = False
        if sid:
            set_session_config(sid, ov)
        if isinstance(config, dict):
            config.setdefault("payload_control", {})["send_personality"] = False
        return "🎭 **Personality & Soul**: 🔴 **DISABLED** (Pure/Raw LLM mode).\n\nPersona character traits, style, and tone directives will not be injected into the system prompt."

    if name_lower in ("on", "enable", "attiva", "abilita", "true", "1", "si", "yes"):
        from hecos.memory.session_config_db import get_session_config, set_session_config
        sid = session_id
        if not sid:
            try:
                from hecos.memory.session_crud import get_sessions
                s = get_sessions()
                if s: sid = s[0].get("id")
            except Exception:
                sid = "default"
        ov = get_session_config(sid) if sid else {}
        ov.setdefault("payload_control", {})["send_personality"] = True
        if sid:
            set_session_config(sid, ov)
        if isinstance(config, dict):
            config.setdefault("payload_control", {})["send_personality"] = True
        return "🎭 **Personality & Soul**: 🟢 **ENABLED**.\n\nActive personality directives will be injected into the prompt."

    if not name:
        return (
            "**Usage:**\n"
            "- `/soul <name_or_index>` — switch personality (e.g. `/soul Motoko` or `/soul 2`)\n"
            "- `/soul off` or `/nosoul` — disable personality directives (Pure LLM)\n"
            "- `/soul on` — re-enable personality directives\n\n"
            "Use `/souls` to list all available personalities."
        )

    try:
        from hecos.modules.personality.main import tools as personality_tools
        return personality_tools.switch_soul(name, config_manager=config_manager)
    except Exception as e:
        return f"❌ Error switching personality: {e}"


def _cmd_nosoul(raw_args_str="", **kwargs) -> str:
    """Direct shortcut to disable personality/soul."""
    return _cmd_soul("off", **kwargs)


def _cmd_payload(raw_args_str="", config=None, session_id=None, **kwargs) -> str:
    """Inspect the last payload metrics and current session toggles."""
    from hecos.core.llm.client import LAST_PAYLOAD_INFO
    from hecos.memory.session_config_db import get_session_config

    sid = session_id
    if not sid:
        try:
            from hecos.memory.session_crud import get_sessions
            sessions = get_sessions()
            if sessions:
                sid = sessions[0].get("id")
        except Exception:
            sid = "default"

    ov = get_session_config(sid) if sid else {}
    p_ctrl = ov.get("payload_control", {})

    cfg_p_ctrl = config.get("payload_control", {}) if isinstance(config, dict) else {}
    tools_on = p_ctrl.get("send_tools", cfg_p_ctrl.get("send_tools", True))
    soul_on = p_ctrl.get("send_personality", cfg_p_ctrl.get("send_personality", True))
    mem_on = p_ctrl.get("send_memory", cfg_p_ctrl.get("send_memory", True))

    badge_tools = "🟢 ON" if tools_on else "🔴 OFF"
    badge_soul = "🟢 ON" if soul_on else "🔴 OFF"
    badge_mem = "🟢 ON" if mem_on else "🔴 OFF"

    lines = [
        "## 📊 Context & Token Payload Inspector\n",
        "### ⚙️ Session Payload Toggles",
        f"- **Tools (Function Schemas):** {badge_tools} *(commands: `/tools on|off`, `/notools`)*",
        f"- **Personality (Soul):** {badge_soul} *(commands: `/soul on|off`, `/nosoul`)*",
        f"- **Memory & History:** {badge_mem} *(commands: `/memory on|off`, `/nomemory`)*",
        "\n### 📦 Last LLM Model Payload",
    ]

    model = LAST_PAYLOAD_INFO.get("model") or (config.get("ai", {}).get("model") if isinstance(config, dict) else "None")
    sys_chars = LAST_PAYLOAD_INFO.get("system_chars", 0)
    user_chars = LAST_PAYLOAD_INFO.get("user_chars", 0)
    tools_chars = LAST_PAYLOAD_INFO.get("tools_chars", 0)
    total_chars = LAST_PAYLOAD_INFO.get("total_chars", 0)
    est_tokens = LAST_PAYLOAD_INFO.get("est_tokens", 0)
    last_ctrl = LAST_PAYLOAD_INFO.get("payload_control", {})
    tools_count = last_ctrl.get("tools_count", 0)

    lines.append(f"- **Model:** `{model}`")
    lines.append(f"- **System + Soul + Memory:** `{sys_chars:,}` chars")
    lines.append(f"- **User Message:** `{user_chars:,}` chars")
    lines.append(f"- **JSON Tool Schemas:** `{tools_chars:,}` chars ({tools_count} tools included)")
    lines.append(f"- **Total Sent:** `{total_chars:,}` chars")
    lines.append(f"- **Prompt Token Estimate:** `~{est_tokens:,}` tokens")

    if LAST_PAYLOAD_INFO.get("timestamp"):
        lines.append(f"- **Timestamp:** `{LAST_PAYLOAD_INFO['timestamp']}`")

    return "\n".join(lines)


def _cmd_diagnostics(raw_args_str="", config=None, config_manager=None, **kwargs) -> str:
    """Run a full system diagnostic report and return it as markdown."""
    try:
        cfg = config or (config_manager.config if config_manager else {})
        from hecos.core.system.diagnostica import run_diagnostics_report
        return run_diagnostics_report(cfg)
    except Exception as e:
        return f"❌ Error during diagnostics: {e}"


def _cmd_speak(raw_args_str="", config=None, config_manager=None, **kwargs) -> str:
    """Direct TTS speech synthesis bypassing the LLM."""
    text = raw_args_str.strip()
    if not text:
        return "🗣️ **Direct TTS Command (LLM Bypass):**\n`/speak <text to pronounce>` (aliases: `/tts`, `/say`, `/parla`, `/voce`)\n*Example:* `/speak Hello Tony, I am Urania!`"
    try:
        from hecos.modules.web_ui.routes_chat_tts import _maybe_generate_tts
        out, audio_id = _maybe_generate_tts(text, config_manager)
        if audio_id:
            return f"🗣️ **Direct Voice Test (LLM Bypass):**\n\n> {text}\n\n✅ Audio generated (`{audio_id}`)"
        else:
            return f"⚠️ Unable to generate audio for: '{text}'. Check TTS server logs."
    except Exception as e:
        return f"❌ Error during voice synthesis: {e}"

_cmd_parla = _cmd_speak


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
        "id": "zz_author",
        "aliases": ["/copyright", "/author", "/credits"],
        "description": "Mostra le informazioni sull'autore e licenza di Hecos",
        "usage": "/copyright",
        "example": "/copyright",
        "icon": "🔏",
        "category": "CORE",
        "requires_auth": "any",
        "requires_args": False,
        "save_to_memory": False,
        "_handler": _cmd_author,
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
        "description": "Switch active personality (name/index) or toggle personality directives (Pure LLM)",
        "usage": "/soul [name|index|on|off]",
        "example": "/soul Motoko",
        "icon": "🎭",
        "category": "PERSONA",
        "requires_auth": "any",
        "requires_args": False,
        "save_to_memory": False,
        "_handler": _cmd_soul,
    },
    {
        "id": "tools",
        "aliases": ["/tools", "/tools_toggle", "/fc"],
        "description": "Enable or disable injecting function calling tool schemas into LLM payload",
        "usage": "/tools [on|off]",
        "example": "/tools off",
        "icon": "🔧",
        "category": "PAYLOAD",
        "requires_auth": "any",
        "requires_args": False,
        "save_to_memory": False,
        "_handler": _cmd_tools,
    },
    {
        "id": "notools",
        "aliases": ["/notools", "/notool", "/disable_tools"],
        "description": "Instantly disable function calling tool schemas (save ~25k tokens)",
        "usage": "/notools",
        "example": "/notools",
        "icon": "⚡",
        "category": "PAYLOAD",
        "requires_auth": "any",
        "requires_args": False,
        "save_to_memory": False,
        "_handler": _cmd_notools,
    },
    {
        "id": "sendtools",
        "aliases": ["/sendtools", "/enable_tools"],
        "description": "Enable injecting function calling tool schemas into prompt",
        "usage": "/sendtools",
        "example": "/sendtools",
        "icon": "🔧",
        "category": "PAYLOAD",
        "requires_auth": "any",
        "requires_args": False,
        "save_to_memory": False,
        "_handler": _cmd_sendtools,
    },
    {
        "id": "nosoul",
        "aliases": ["/nosoul", "/raw", "/pure_llm"],
        "description": "Disable personality/soul directives in prompt (Pure LLM mode)",
        "usage": "/nosoul",
        "example": "/nosoul",
        "icon": "🎭",
        "category": "PAYLOAD",
        "requires_auth": "any",
        "requires_args": False,
        "save_to_memory": False,
        "_handler": _cmd_nosoul,
    },
    {
        "id": "memory_toggle",
        "aliases": ["/memory", "/memoria"],
        "description": "Enable or disable injecting memory vault and chat history into prompt",
        "usage": "/memory [on|off]",
        "example": "/memory off",
        "icon": "🧠",
        "category": "PAYLOAD",
        "requires_auth": "any",
        "requires_args": False,
        "save_to_memory": False,
        "_handler": _cmd_memory,
    },
    {
        "id": "nomemory",
        "aliases": ["/nomemory", "/nomem"],
        "description": "Disable injecting memory vault and chat history into prompt",
        "usage": "/nomemory",
        "example": "/nomemory",
        "icon": "🧹",
        "category": "PAYLOAD",
        "requires_auth": "any",
        "requires_args": False,
        "save_to_memory": False,
        "_handler": _cmd_nomemory,
    },
    {
        "id": "payload",
        "aliases": ["/payload", "/context", "/tokens"],
        "description": "Display payload composition inspector (chars, tokens, tools status)",
        "usage": "/payload",
        "example": "/payload",
        "icon": "📊",
        "category": "PAYLOAD",
        "requires_auth": "any",
        "requires_args": False,
        "save_to_memory": False,
        "_handler": _cmd_payload,
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
    {
        "id": "diagnostics",
        "aliases": ["/diagnostics", "/diag", "/diagnosi"],
        "description": "Runs full system diagnostics (CPU, RAM, plugins, backend)",
        "usage": "/diagnostics",
        "example": "/diagnostics",
        "icon": "🔍",
        "category": "CORE",
        "requires_auth": "admin",
        "requires_args": False,
        "save_to_memory": False,
        "_handler": _cmd_diagnostics,
    },
    {
        "id": "show",
        "aliases": ["/show", "/file", "/anteprima"],
        "description": "Mostra l'anteprima di un file locale in chat (con Visual Editor per HTML)",
        "usage": "/show <percorso_o_nome_file>",
        "example": "/show mio_documento.html",
        "icon": "📄",
        "category": "CORE",
        "requires_auth": "any",
        "requires_args": True,
        "save_to_memory": False,
        "_handler": _cmd_show,
    },
    {
        "id": "docs",
        "aliases": ["/docs", "/documenti", "/docs_list"],
        "description": "Elenca tutti i documenti in media/documents con link cliccabili",
        "usage": "/docs [filtro]",
        "example": "/docs rivista",
        "icon": "📁",
        "category": "CORE",
        "requires_auth": "any",
        "requires_args": False,
        "save_to_memory": False,
        "_handler": _cmd_docs_list,
    },
    {
        "id": "speak",
        "aliases": ["/speak", "/tts", "/say", "/parla", "/voce"],
        "description": "Direct TTS speech synthesis bypassing the LLM",
        "usage": "/speak <text to pronounce>",
        "example": "/speak Hello Tony, I am Urania!",
        "icon": "🗣️",
        "category": "AUDIO",
        "requires_auth": "any",
        "requires_args": True,
        "save_to_memory": True,
        "_handler": _cmd_speak,
    },
]
