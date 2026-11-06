"""
hecos/core/commands/builtins/persona_commands.py
Built-in slash commands for AI Personality management:
/souls, /soul
"""

import os
from typing import Any, Dict, List


def _cmd_souls(raw_args_str: str = "", config=None, config_manager=None, **kwargs) -> str:
    """List all available AI personalities (souls)."""
    try:
        from hecos.modules.personality.main import tools as personality_tools
        return personality_tools.list_souls(config_manager=config_manager)
    except Exception:
        # Fallback: scan the personas directory directly
        try:
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
                lines.append(f"{i + 1}. **{name}**{marker}")
            lines.append("\n*Usa `/soul <nome>` per cambiare.*")
            return "\n".join(lines)
        except Exception as e2:
            return f"❌ Errore: {e2}"


def _cmd_soul(
    raw_args_str: str = "",
    config=None,
    config_manager=None,
    session_id=None,
    **kwargs,
) -> str:
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
                if s:
                    sid = s[0].get("id")
            except Exception:
                sid = "default"
        ov = get_session_config(sid) if sid else {}
        ov.setdefault("payload_control", {})["send_personality"] = False
        if sid:
            set_session_config(sid, ov)
        if isinstance(config, dict):
            config.setdefault("payload_control", {})["send_personality"] = False
        return (
            "🎭 **Personality & Soul**: 🔴 **DISABLED** (Pure/Raw LLM mode).\n\n"
            "Persona character traits, style, and tone directives will not be injected into the system prompt."
        )

    if name_lower in ("on", "enable", "attiva", "abilita", "true", "1", "si", "yes"):
        from hecos.memory.session_config_db import get_session_config, set_session_config
        sid = session_id
        if not sid:
            try:
                from hecos.memory.session_crud import get_sessions
                s = get_sessions()
                if s:
                    sid = s[0].get("id")
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


def _cmd_nosoul(raw_args_str: str = "", **kwargs) -> str:
    """Direct shortcut to disable personality/soul."""
    return _cmd_soul("off", **kwargs)


PERSONA_COMMANDS: List[Dict[str, Any]] = [
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
]

