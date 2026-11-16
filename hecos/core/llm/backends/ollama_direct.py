"""
hecos/core/llm/backends/ollama_direct.py
Direct HTTP communication with Ollama /v1/chat/completions.
Preserves reasoning/thinking fields, supports native & fallback tool calling,
and monitors GPU residency.

NOTE on think parameter:
  - /v1/chat/completions does NOT honor think=false (Ollama limitation as of 2024)
  - /api/chat DOES honor think=false at root level
  - When think=False is requested, we use /api/chat and adapt the response format
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


def _to_native_ollama_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Converts OpenAI-format messages into native Ollama /api/chat format:
    - Parses assistant `tool_calls[].function.arguments` from JSON string into dict
      (Ollama /api/chat rejects string arguments with 400).
    - Ensures tool result messages carry clean string content without mutating caller history.
    """
    native_msgs: List[Dict[str, Any]] = []
    for m in messages or []:
        if not isinstance(m, dict):
            native_msgs.append(m)
            continue
        m_copy = dict(m)
        if m_copy.get("role") == "assistant" and isinstance(m_copy.get("tool_calls"), list):
            fixed_tcs = []
            for tc in m_copy["tool_calls"]:
                if not isinstance(tc, dict):
                    continue
                fn = tc.get("function") or {}
                raw_args = fn.get("arguments", {})
                if isinstance(raw_args, str):
                    try:
                        parsed_args = json.loads(raw_args) if raw_args.strip() else {}
                        if not isinstance(parsed_args, dict):
                            parsed_args = {"value": parsed_args}
                    except Exception:
                        parsed_args = {}
                elif isinstance(raw_args, dict):
                    parsed_args = raw_args
                else:
                    parsed_args = {}
                tc_out: Dict[str, Any] = {
                    "function": {
                        "name": str(fn.get("name") or ""),
                        "arguments": parsed_args,
                    }
                }
                if tc.get("id"):
                    tc_out["id"] = tc["id"]
                if tc.get("type"):
                    tc_out["type"] = tc["type"]
                fixed_tcs.append(tc_out)
            if fixed_tcs:
                m_copy["tool_calls"] = fixed_tcs
            else:
                m_copy.pop("tool_calls", None)
        elif m_copy.get("role") == "tool" and m_copy.get("content") is not None and not isinstance(m_copy.get("content"), str):
            m_copy["content"] = str(m_copy["content"])
        native_msgs.append(m_copy)
    return native_msgs


def _call_api_chat(ollama_base: str, ollama_body_v1: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calls /api/chat (Ollama native format) and normalizes response to OpenAI-like format.
    Used when think=False is required (only /api/chat honors think at root level).
    """
    api_chat_url = f"{ollama_base}/api/chat"

    # Convert OpenAI-compat body to native Ollama /api/chat format
    native_body: Dict[str, Any] = {
        "model": ollama_body_v1.get("model", ""),
        "messages": _to_native_ollama_messages(ollama_body_v1.get("messages", [])),
        "stream": False,
        "think": ollama_body_v1.get("think", False),
    }

    # Pass options if present
    if "options" in ollama_body_v1:
        native_body["options"] = ollama_body_v1["options"]
    else:
        native_opts = {}
        if "temperature" in ollama_body_v1:
            native_opts["temperature"] = ollama_body_v1["temperature"]
        if "top_p" in ollama_body_v1:
            native_opts["top_p"] = ollama_body_v1["top_p"]
        if native_opts:
            native_body["options"] = native_opts

    # Tools are not passed since think=False is for fast/no-reasoning responses
    if ollama_body_v1.get("tools"):
        native_body["tools"] = ollama_body_v1["tools"]

    zlog_debug("LiteLLM", f"[OLLAMA-DIRECT] /api/chat with think={ollama_body_v1.get('think')} model={native_body['model']}")
    resp = requests.post(api_chat_url, json=native_body, timeout=params.get("timeout", 300))
    if resp.status_code >= 400:
        zlog_error(f"[OLLAMA-DIRECT] /api/chat HTTP {resp.status_code}: {resp.text[:500]}")
    resp.raise_for_status()
    native_data = resp.json()

    # Normalize to OpenAI-compat format for uniform downstream parsing
    native_msg = native_data.get("message", {})
    normalized = {
        "choices": [{
            "message": {
                "role": native_msg.get("role", "assistant"),
                "content": native_msg.get("content", ""),
                "reasoning": native_msg.get("thinking", ""),  # /api/chat uses "thinking" field
                "tool_calls": native_msg.get("tool_calls"),
            },
            "finish_reason": "stop" if native_data.get("done") else None,
        }],
        "usage": {
            "prompt_tokens": native_data.get("prompt_eval_count", 0),
            "completion_tokens": native_data.get("eval_count", 0),
            "total_tokens": native_data.get("prompt_eval_count", 0) + native_data.get("eval_count", 0),
        },
    }
    return normalized


_HIST_STREAM_BADGE_RE = re.compile(
    r"(?m)^\s*(?:>\s*)?(?:📺\s*Tuned to|⏹️\s*Live Stream stopped|⏯️\s*Playback)[^\r\n]*$"
)


def _rewrite_assistant_stream_badges(content: str) -> str:
    """Replaces stored UI stream status blockquotes with explicit tool-call context for text-mode LLMs."""
    if not content or not any(tok in content for tok in ("📺 Tuned to", "⏹️ Live Stream stopped", "⏯️ Playback")):
        return content

    def _repl(match: re.Match) -> str:
        line = re.sub(r"^\s*>\s*", "", match.group(0)).strip()
        return f"[System Note: You previously executed NETSEARCH__stream_control(...) which returned -> {line}]"

    return _HIST_STREAM_BADGE_RE.sub(_repl, content)


def _normalize_messages_for_ollama(messages: List[Dict[str, Any]], has_tools: bool) -> List[Dict[str, Any]]:
    """
    Normalizes OpenAI-style history cleanly for Ollama:
    1. Converts orphan `role='tool'` entries (when native tools are off OR when the preceding
       assistant turn used inline text/JSON fallback without structured `tool_calls`) into clean
       `role='user'` execution summaries so ChatML never emits stray `<tool_response>` loops.
    2. Rewrites stored assistant '📺 Tuned to ...' UI badges into explicit tool execution reminders
       so text-mode models do not mimic the badge directly instead of calling NETSEARCH__stream_control(...).
    """
    out: List[Dict[str, Any]] = []
    last_asst_had_tool_calls = False
    for m in messages or []:
        if not isinstance(m, dict):
            out.append(m)
            continue
        role = m.get("role")
        if role == "tool":
            if has_tools and last_asst_had_tool_calls:
                out.append(m)
                continue
            t_name = m.get("name") or "TOOL"
            t_content = m.get("content") or ""
            guidance = (
                "Based strictly on this real tool result above, run the next required tool call "
                "(or summarize concisely once all deliverables are verified). Never echo <tool_response> tags."
                if has_tools
                else (
                    "Now reply in character to the user based strictly on this real tool result. "
                    "Do not print raw function call syntax unless invoking another required action."
                )
            )
            out.append({
                "role": "user",
                "content": f"[TOOL EXECUTION RESULT · {t_name}]:\n{t_content}\n\n{guidance}",
            })
        elif role == "assistant":
            last_asst_had_tool_calls = bool(m.get("tool_calls"))
            if not has_tools and isinstance(m.get("content"), str):
                rewritten = _rewrite_assistant_stream_badges(m["content"])
                if rewritten != m["content"]:
                    m_copy = dict(m)
                    m_copy["content"] = rewritten
                    out.append(m_copy)
                    continue
            out.append(m)
        else:
            last_asst_had_tool_calls = False
            out.append(m)
    return out


def execute_ollama_direct(params: Dict[str, Any], stream: bool = False) -> Any:
    """
    Directly invokes Ollama's /v1/chat/completions endpoint (or /api/chat when think=False).
    Bypasses LiteLLM to preserve reasoning fields, avoid dropped tools,
    and accurately record GPU residency metrics.
    """
    ollama_base = params.get("api_base", "http://localhost:11434").rstrip("/")
    ollama_url = f"{ollama_base}/v1/chat/completions"

    has_native_tools = bool(params.get("tools"))
    # Translate LiteLLM params to OpenAI format for Ollama
    ollama_body: Dict[str, Any] = {
        "model": params["model"].replace("ollama/", "", 1),
        "messages": _normalize_messages_for_ollama(params["messages"], has_native_tools),
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
    if extra_body and "think" in extra_body:
        # NOTE: Gemma4 and Ollama require "think" at ROOT body level, NOT inside options{}
        # Also: /v1/chat/completions ignores think=False; we route to /api/chat in that case
        ollama_body["think"] = extra_body["think"]

    # Route to /api/chat when think=False (only endpoint that honors this for Gemma4)
    use_api_chat = ollama_body.get("think") is False
    if use_api_chat:
        zlog_info("LiteLLM", "[OLLAMA-DIRECT] think=False requested -> routing to /api/chat (OpenAI compat ignores think param)")
        data = _call_api_chat(ollama_base, ollama_body, params)
    else:
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
                # Inject think=False at ROOT level and route to /api/chat
                retry_body["think"] = False
                retry_data = _call_api_chat(ollama_base, retry_body, params)
                c2 = (retry_data.get("choices", [{}])[0].get("message", {}).get("content") or "").strip()
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
