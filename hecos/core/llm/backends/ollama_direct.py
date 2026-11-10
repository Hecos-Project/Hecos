"""
hecos/core/llm/backends/ollama_direct.py
Direct HTTP communication with Ollama /v1/chat/completions.
Preserves reasoning/thinking fields, supports native & fallback tool calling,
and monitors GPU residency.
"""

import json
import re
import time
from typing import Any, Dict, List, Optional, Union
import requests

from hecos.core.logging.logger import (
    debug as zlog_debug,
    info as zlog_info,
    error as zlog_error,
)
from hecos.core.llm.payload_tracker import update_usage_telemetry, LAST_PAYLOAD_INFO


class _SyntheticCall:
    def __init__(self, tc_dict: dict):
        self.id = tc_dict.get("id", f"call_{int(time.time())}")
        class _Fn:
            pass
        self.function = _Fn()
        self.function.name = tc_dict.get("function", {}).get("name", "")
        raw_args = tc_dict.get("function", {}).get("arguments", {})
        self.function.arguments = json.dumps(raw_args) if isinstance(raw_args, dict) else (raw_args or "{}")


class SyntheticAssistantMessage:
    """Synthetic assistant message object for tool calls dispatched to tool_dispatcher."""

    def __init__(self, tool_calls_raw: list, content: str = ""):
        self.role = "assistant"
        self.content = content or ""
        self.tool_calls = [_SyntheticCall(tc) for tc in tool_calls_raw]

    def model_dump(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            "tool_calls": [
                {
                    "id": c.id,
                    "type": "function",
                    "function": {"name": c.function.name, "arguments": c.function.arguments},
                }
                for c in self.tool_calls
            ],
        }


def execute_ollama_direct(params: Dict[str, Any], stream: bool = False) -> Any:
    """
    Directly invokes Ollama's /v1/chat/completions endpoint.
    Bypasses LiteLLM to preserve reasoning fields, avoid dropped tools,
    and accurately record GPU residency metrics.
    """
    ollama_base = params.get("api_base", "http://localhost:11434").rstrip("/")
    ollama_url = f"{ollama_base}/v1/chat/completions"

    # Translate LiteLLM params to OpenAI format for Ollama
    ollama_body: Dict[str, Any] = {
        "model": params["model"].replace("ollama/", "", 1),
        "messages": params["messages"],
        "temperature": params.get("temperature", 0.7),
        "top_p": params.get("top_p", 0.9),
        "stream": False,
    }

    if params.get("tools"):
        ollama_body["tools"] = params["tools"]
        zlog_debug("LiteLLM", f"[OLLAMA-DIRECT] Sending {len(params['tools'])} tools to Ollama")

    extra_body = params.get("extra_body")
    if extra_body and "options" in extra_body:
        ollama_body["options"] = extra_body["options"]

    zlog_debug("LiteLLM", f"[OLLAMA-DIRECT] POST {ollama_url} model={ollama_body['model']}")

    resp = requests.post(ollama_url, json=ollama_body, timeout=params.get("timeout", 300))
    resp.raise_for_status()
    data = resp.json()

    msg = data.get("choices", [{}])[0].get("message", {})
    content = (msg.get("content") or "").strip()
    reasoning = msg.get("reasoning") or msg.get("reasoning_content") or ""

    # Telemetry and GPU VRAM residency
    try:
        usage = data.get("usage", {})
        if usage:
            update_usage_telemetry(usage)

        try:
            ps_resp = requests.get(f"{ollama_base}/api/ps", timeout=1.0).json()
            for pm in ps_resp.get("models", []):
                m_clean = params["model"].replace("ollama/", "")
                if pm.get("name") == m_clean or pm.get("name", "").startswith(m_clean.split(":")[0]):
                    sz_mb = pm.get("size", 0) / (1024 * 1024)
                    vr_mb = pm.get("size_vram", 0) / (1024 * 1024)
                    pct = (vr_mb / sz_mb * 100) if sz_mb > 0 else 0
                    zlog_info(
                        "LiteLLM",
                        f"[GPU MONITOR] Model '{pm.get('name')}' resident in VRAM: "
                        f"{vr_mb:.0f} MB / {sz_mb:.0f} MB ({pct:.1f}%)",
                    )
        except Exception:
            pass
    except Exception:
        pass

    # 1. Native tool calls
    tool_calls = msg.get("tool_calls")
    if tool_calls:
        zlog_debug("LiteLLM", f"[OLLAMA-DIRECT] Tool calls detected ({len(tool_calls)}): {tool_calls}")
        return SyntheticAssistantMessage(tool_calls, content)

    # 2. Fallback JSON tool_calls parsed from text
    if not tool_calls and content:
        tc_match = re.search(r'\{[^{}]*"tool_calls"\s*:\s*\[.*?\]\s*\}', content, re.DOTALL)
        if tc_match:
            try:
                parsed_tc = json.loads(tc_match.group())
                if parsed_tc.get("tool_calls"):
                    zlog_info("LiteLLM", "[OLLAMA-DIRECT] Recovered tool_calls from text output (fallback JSON parser)")
                    return SyntheticAssistantMessage(parsed_tc["tool_calls"], "")
            except json.JSONDecodeError:
                pass

    zlog_debug("LiteLLM", f"[OLLAMA-DIRECT] content={len(content)} chars | reasoning={len(reasoning)} chars")

    if reasoning:
        zlog_info("LiteLLM", f"[REASONING] Captured {len(reasoning)} chars of thinking from Ollama reasoning field")
        content = re.sub(r'^(HECOS|Hecos|hecos)\s*:\s*', '', content, flags=re.IGNORECASE)

        # If content is empty (all tokens consumed by thinking), retry once without thinking enabled
        if not content.strip():
            zlog_info("LiteLLM", "[REASONING] content=0 after thinking — retrying without thinking for actual response")
            try:
                retry_body = dict(ollama_body)
                # Inject thinking=False in options to suppress thinking on retry
                retry_opts = dict(retry_body.get("options", {}))
                retry_opts["think"] = False
                retry_body["options"] = retry_opts
                # Inject the reasoning as assistant context note in the last user message
                r2 = requests.post(ollama_url, json=retry_body, timeout=params.get("timeout", 300))
                r2.raise_for_status()
                d2 = r2.json()
                c2 = (d2.get("choices", [{}])[0].get("message", {}).get("content") or "").strip()
                if c2:
                    zlog_info("LiteLLM", f"[REASONING] Retry succeeded — got {len(c2)} chars")
                    c2 = re.sub(r'^(HECOS|Hecos|hecos)\s*:\s*', '', c2, flags=re.IGNORECASE)
                    return f"<think>\n{reasoning}\n</think>\n\n{c2}"
                else:
                    zlog_info("LiteLLM", "[REASONING] Retry also empty — returning thinking-only block")
            except Exception as _retry_err:
                zlog_error(f"LiteLLM: [REASONING] Retry failed: {_retry_err}")

        return f"<think>\n{reasoning}\n</think>\n\n{content}"

    if not content:
        finish = data.get("choices", [{}])[0].get("finish_reason")
        if finish == "content_filter":
            zlog_error("LiteLLM: Response BLOCKED by safety filter.")
            return "!!!BLOCK_SAFETY!!!"
        return ""

    content = re.sub(r'^(HECOS|Hecos|hecos)\s*:\s*', '', content, flags=re.IGNORECASE)
    return content

