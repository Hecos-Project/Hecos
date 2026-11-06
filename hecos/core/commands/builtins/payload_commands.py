"""
hecos/core/commands/builtins/payload_commands.py
Built-in slash commands for token optimization, context payload controls, and telemetry:
/tools, /notools, /sendtools, /memory, /nomemory, /payload
"""

from typing import Any, Dict, List


def _cmd_tools(raw_args_str: str = "", config=None, session_id=None, **kwargs) -> str:
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
        return "⚠️ **Uso:** `/tools on` oppure `/tools off` (oppure comando rapido `/notools`)"

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
    return (
        f"🔧 **Function Calling Tools**: {status_str}\n\n"
        f"{tip}\n\n"
        f"*Use `/payload` to inspect current payload metrics or `/tools` to toggle.*"
    )


def _cmd_notools(raw_args_str: str = "", **kwargs) -> str:
    """Direct shortcut to disable tools."""
    return _cmd_tools("off", **kwargs)


def _cmd_sendtools(raw_args_str: str = "", **kwargs) -> str:
    """Direct shortcut to enable tools."""
    return _cmd_tools("on", **kwargs)


def _cmd_memory(raw_args_str: str = "", config=None, session_id=None, **kwargs) -> str:
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
        return "⚠️ **Uso:** `/memory on` oppure `/memory off` (oppure comando rapido `/nomemory`)"

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
    return (
        f"🧠 **Memory & History**: {status_str}\n\n"
        f"{tip}\n\n"
        f"*Use `/payload` to inspect current payload metrics or `/memory` to toggle.*"
    )


def _cmd_nomemory(raw_args_str: str = "", **kwargs) -> str:
    """Direct shortcut to disable memory."""
    return _cmd_memory("off", **kwargs)


def _cmd_payload(raw_args_str: str = "", config=None, session_id=None, **kwargs) -> str:
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

    model = LAST_PAYLOAD_INFO.get("model") or (
        config.get("ai", {}).get("model") if isinstance(config, dict) else "None"
    )
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


PAYLOAD_COMMANDS: List[Dict[str, Any]] = [
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
]

