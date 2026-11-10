"""
hecos/core/llm/payload_tracker.py
Tracks payload telemetry, token estimates, tool schemas cost, and active model state.
"""

import os
import json
import datetime
from typing import Any, Dict, Optional

from hecos.core.logging.logger import debug as zlog_debug, info as zlog_info

# Global variable to store last payload metadata for WebUI inspection
LAST_PAYLOAD_INFO: Dict[str, Any] = {
    "model": "None",
    "provider": "None",
    "system_chars": 0,
    "user_chars": 0,
    "tools_chars": 0,
    "total_chars": 0,
    "approx_tokens": 0,
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "messages_count": 0,
    "messages_preview": [],
    "plugins_cost": {},
    "payload_control": {
        "send_tools": True,
        "tools_count": 0,
        "send_personality": True,
        "send_memory": True,
    },
}


def get_active_model(cfg: Optional[dict] = None) -> str:
    """Returns the name of the last actively used model, falling back to config."""
    if LAST_PAYLOAD_INFO.get("model") != "None":
        return str(LAST_PAYLOAD_INFO["model"])
    if cfg:
        btype = cfg.get("backend", {}).get("type", "ollama")
        if btype == "hybrid":
            cloud_m = cfg.get("backend", {}).get("cloud", {}).get("model", "")
            if cloud_m:
                return str(cloud_m)
            btype = "ollama"
        return str(cfg.get("backend", {}).get(btype, {}).get("model", "?"))
    return "?"


def analyze_and_record_payload(
    params: Dict[str, Any],
    model_name: str,
    backend_type: str,
    specific_config: Dict[str, Any],
) -> None:
    """Calculates characters, token approximations, and tool schemas overhead."""
    try:
        messages = params.get("messages", [])
        tools = params.get("tools", [])

        sys_chars = sum(len(str(m.get('content', ''))) for m in messages if m.get('role') == 'system')
        usr_chars = sum(len(str(m.get('content', ''))) for m in messages if m.get('role') != 'system')
        tls_chars = len(json.dumps(tools)) if tools else 0
        tot_chars = sys_chars + usr_chars + tls_chars

        plugins_cost: Dict[str, int] = {}
        for tool in tools:
            try:
                name = tool.get("function", {}).get("name", "")
                tag = name.split("__")[0] if "__" in name else "CORE_TOOLS"
                tool_size = len(json.dumps(tool))
                plugins_cost[tag] = plugins_cost.get(tag, 0) + tool_size
            except Exception:
                pass

        preview_msgs = []
        for pm in messages[-2:]:
            pm_cnt = str(pm.get("content") or "")
            if len(pm_cnt) > 600:
                pm_cnt = pm_cnt[:600] + " ... [TRUNCATED]"
            preview_msgs.append({"role": pm.get("role", "unknown"), "content": pm_cnt})

        pctrl = specific_config.get("payload_control") or {}
        tools_on = bool(tools)
        tools_cnt = len(tools)

        LAST_PAYLOAD_INFO.update({
            "model": model_name,
            "provider": backend_type,
            "system_chars": sys_chars,
            "user_chars": usr_chars,
            "tools_chars": tls_chars,
            "total_chars": tot_chars,
            "approx_tokens": tot_chars // 3,  # Approximate 1 token ~ 3-4 chars
            "prompt_tokens": 0,               # Reset prior counters
            "completion_tokens": 0,
            "messages_count": len(messages),
            "messages_preview": preview_msgs,
            "plugins_cost": plugins_cost,
            "payload_control": {
                "send_tools": tools_on,
                "tools_count": tools_cnt,
                "send_personality": pctrl.get("send_personality", True),
                "send_memory": pctrl.get("send_memory", True),
                "include_thinking": pctrl.get("include_thinking_in_history", False),
            },
        })

        t_label = f"ON ({tools_cnt} tools, {tls_chars:,} chars)" if tools_on else "OFF (0 chars)"
        approx_t = tot_chars // 3
        zlog_info(
            "LiteLLM",
            f"[PAYLOAD CONTROL] Tools: {t_label} | System: {sys_chars:,} chars | "
            f"User: {usr_chars:,} chars | Prompt: ~{approx_t:,} tokens",
        )
    except Exception as e:
        zlog_debug("LiteLLM", f"Payload analysis skipped: {e}")


def update_usage_telemetry(usage: Any) -> None:
    """Updates real token counts from provider usage metadata."""
    if not usage:
        return
    try:
        if isinstance(usage, dict):
            pt = usage.get("prompt_tokens", 0)
            ct = usage.get("completion_tokens", 0)
            tt = usage.get("total_tokens", LAST_PAYLOAD_INFO["approx_tokens"])
        else:
            pt = getattr(usage, "prompt_tokens", 0)
            ct = getattr(usage, "completion_tokens", 0)
            tt = getattr(usage, "total_tokens", LAST_PAYLOAD_INFO["approx_tokens"])

        LAST_PAYLOAD_INFO["prompt_tokens"] = pt
        LAST_PAYLOAD_INFO["completion_tokens"] = ct
        LAST_PAYLOAD_INFO["approx_tokens"] = tt
    except Exception:
        pass


def dump_debug_payload(params: Dict[str, Any], model_name: str) -> None:
    """Dumps request parameters and payload structure to logs/payloads.log."""
    try:
        from hecos.core.constants import LOGS_DIR
        payload_log_path = os.path.join(LOGS_DIR, "payloads.log")
        dump_data = {
            "timestamp": datetime.datetime.now().isoformat(),
            "model": model_name,
            "messages": params.get("messages", []),
            "tools": params.get("tools", []),
            "ollama_options": params.get("extra_body", {}).get("options", {}),
            "think_param": params.get("extra_body", {}).get("think", "<not set>"),
        }
        with open(payload_log_path, "a", encoding="utf-8") as pf:
            pf.write("\n" + "=" * 80 + "\n")
            pf.write(f"=== PAYLOAD START | {dump_data['timestamp']} | model: {model_name} ===\n")
            pf.write("=" * 80 + "\n\n")
            pf.write(json.dumps(dump_data, indent=2))
            pf.write("\n\n" + "=" * 80 + "\n")
            pf.write(f"=== PAYLOAD END | {dump_data['timestamp']} ===\n")
            pf.write("=" * 80 + "\n")
    except Exception as e:
        zlog_debug("LiteLLM", f"Could not dump payload to log: {e}")

