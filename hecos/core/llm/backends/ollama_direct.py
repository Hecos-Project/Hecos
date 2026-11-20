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

import http.client
import json
import re
import select
import socket
import struct
import threading
import time
import urllib.parse
from typing import Any, Dict, List, Optional, Union
import requests

from hecos.core.logging.logger import (
    debug as zlog_debug,
    info as zlog_info,
    error as zlog_error,
)
from hecos.core.llm.payload_tracker import update_usage_telemetry, LAST_PAYLOAD_INFO


class _OllamaAbortedError(RuntimeError):
    """Raised internally when the active turn's cancel_event interrupts an Ollama HTTP call."""


def _resolve_active_cancel_event() -> Optional[threading.Event]:
    try:
        from hecos.core.agent.trace_session import get_active_session
        sess = get_active_session()
        if sess is not None:
            return getattr(sess, "cancel_event", None)
    except Exception:
        pass
    return None


def _post_json_cancellable(
    url: str,
    payload: Dict[str, Any],
    *,
    timeout: float = 900.0,
    cancel_event: Optional[threading.Event] = None,
) -> Dict[str, Any]:
    """
    POST JSON to Ollama using a cancellable socket so clicking Stop or starting a new turn
    immediately terminates both the blocked Python wait and the Ollama server context.
    """
    eff_event = cancel_event or _resolve_active_cancel_event()
    if eff_event is not None and eff_event.is_set():
        raise _OllamaAbortedError("Turn cancelled before sending Ollama request")

    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        resp = requests.post(url, json=payload, timeout=timeout)
        resp.raise_for_status()
        return resp.json()

    host = parsed.hostname
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"

    conn_cls = http.client.HTTPSConnection if parsed.scheme == "https" else http.client.HTTPConnection
    conn = conn_cls(host, port, timeout=timeout)
    hook_registered = False

    def _abort_conn() -> None:
        sock = getattr(conn, "sock", None)
        if sock is not None:
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
            except Exception:
                pass
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            try:
                sock.close()
            except Exception:
                pass
        try:
            conn.close()
        except Exception:
            pass

    try:
        conn.connect()
        if eff_event is not None:
            from hecos.core.agent.turn_control import register_abort_hook
            hook_registered = register_abort_hook(eff_event, _abort_conn)
            if eff_event.is_set():
                raise _OllamaAbortedError("Turn cancelled during Ollama connect")

        body_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Content-Length": str(len(body_bytes)),
        }
        conn.request("POST", path, body=body_bytes, headers=headers)

        # Wait interruptibly BEFORE HTTPResponse creates a buffered socket reader (_io_refs += 1),
        # so Windows closesocket() executes immediately without blocking in C recv().
        if eff_event is not None:
            deadline = time.monotonic() + float(timeout or 900.0)
            while True:
                if eff_event.is_set():
                    _abort_conn()
                    raise _OllamaAbortedError("Turn cancelled while awaiting Ollama response")
                sock = getattr(conn, "sock", None)
                if sock is None:
                    break
                if hasattr(sock, "pending") and sock.pending() > 0:
                    break
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise requests.Timeout(f"Read timed out after {timeout}s")
                wait_slice = min(0.15, remaining)
                try:
                    readable, _, _ = select.select([sock], [], [], wait_slice)
                except (ValueError, OSError):
                    if eff_event.is_set():
                        raise _OllamaAbortedError("Ollama socket aborted")
                    break
                if readable:
                    break

        resp = conn.getresponse()
        raw_bytes = resp.read()
        raw_text = raw_bytes.decode("utf-8", errors="replace")

        if eff_event is not None and eff_event.is_set():
            raise _OllamaAbortedError("Turn cancelled while awaiting Ollama response")

        if resp.status >= 400:
            zlog_error(f"[OLLAMA-DIRECT] HTTP {resp.status} for {path}: {raw_text[:500]}")
            err = requests.HTTPError(
                f"{resp.status} Server Error: {resp.reason} for url: {url}"
            )
            raise err

        return json.loads(raw_text) if raw_text.strip() else {}
    except _OllamaAbortedError:
        raise
    except (TimeoutError, socket.timeout, requests.Timeout) as exc:
        if eff_event is not None and eff_event.is_set():
            raise _OllamaAbortedError("Ollama request aborted by user/new turn") from exc
        if isinstance(exc, requests.Timeout):
            raise
        raise requests.Timeout(str(exc)) from exc
    except (OSError, http.client.HTTPException) as exc:
        if eff_event is not None and eff_event.is_set():
            raise _OllamaAbortedError("Ollama request aborted by user/new turn") from exc
        if "timed out" in str(exc).lower() or "timeout" in str(exc).lower():
            raise requests.Timeout(str(exc)) from exc
        raise requests.ConnectionError(str(exc)) from exc
    finally:
        if hook_registered and eff_event is not None:
            try:
                from hecos.core.agent.turn_control import unregister_abort_hook
                unregister_abort_hook(eff_event, _abort_conn)
            except Exception:
                pass
        try:
            conn.close()
        except Exception:
            pass


def _emit_streaming_heartbeat() -> None:
    """Keep WebUI inference watchdog alive while tokens stream from slow local models."""
    try:
        from hecos.core.agent.trace_session import get_active_session
        sess = get_active_session()
        if sess is not None and sess.trace_callback is not None:
            sess.trace_callback({"type": "heartbeat"}, "debug")
    except Exception:
        pass


def _post_ollama_chat_stream_cancellable(
    url: str,
    payload: Dict[str, Any],
    *,
    timeout: float = 900.0,
    cancel_event: Optional[threading.Event] = None,
) -> Dict[str, Any]:
    """
    POST JSON to Ollama `/api/chat` with `stream=True` (NDJSON) and cancellable sockets.
    Streaming avoids premature read timeouts during long CPU/GPU generations while letting
    the Stop button abort active requests within ~0.15s and resetting the inference watchdog.
    """
    eff_event = cancel_event or _resolve_active_cancel_event()
    if eff_event is not None and eff_event.is_set():
        raise _OllamaAbortedError("Turn cancelled before sending Ollama request")

    stream_payload = dict(payload)
    stream_payload["stream"] = True

    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return _post_json_cancellable(url, {**stream_payload, "stream": False}, timeout=timeout, cancel_event=eff_event)

    host = parsed.hostname
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"

    base_timeout = float(timeout or 900.0)
    conn_cls = http.client.HTTPSConnection if parsed.scheme == "https" else http.client.HTTPConnection
    conn = conn_cls(host, port, timeout=base_timeout)
    hook_registered = False

    def _abort_conn() -> None:
        sock = getattr(conn, "sock", None)
        if sock is not None:
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
            except Exception:
                pass
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            try:
                sock.close()
            except Exception:
                pass
        try:
            conn.close()
        except Exception:
            pass

    def _await_sock_readable(sock, deadline_ts: float) -> None:
        while True:
            if eff_event is not None and eff_event.is_set():
                _abort_conn()
                raise _OllamaAbortedError("Turn cancelled while awaiting Ollama stream")
            if sock is None:
                return
            if hasattr(sock, "pending") and sock.pending() > 0:
                return
            remaining = deadline_ts - time.monotonic()
            if remaining <= 0:
                raise requests.Timeout(f"Read timed out after {base_timeout}s")
            wait_slice = min(0.15, remaining) if eff_event is not None else min(1.0, remaining)
            try:
                readable, _, _ = select.select([sock], [], [], wait_slice)
            except (ValueError, OSError):
                if eff_event is not None and eff_event.is_set():
                    raise _OllamaAbortedError("Ollama socket aborted")
                return
            if readable:
                return

    try:
        conn.connect()
        if eff_event is not None:
            from hecos.core.agent.turn_control import register_abort_hook
            hook_registered = register_abort_hook(eff_event, _abort_conn)
            if eff_event.is_set():
                raise _OllamaAbortedError("Turn cancelled during Ollama connect")

        body_bytes = json.dumps(stream_payload, ensure_ascii=False).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/x-ndjson, application/json",
            "Content-Length": str(len(body_bytes)),
        }
        conn.request("POST", path, body=body_bytes, headers=headers)

        t_start = time.monotonic()
        prefill_deadline = t_start + base_timeout
        _await_sock_readable(getattr(conn, "sock", None), prefill_deadline)

        resp = conn.getresponse()
        if resp.status >= 400:
            raw_err = resp.read().decode("utf-8", errors="replace")
            zlog_error(f"[OLLAMA-DIRECT] HTTP {resp.status} for {path}: {raw_err[:500]}")
            raise requests.HTTPError(f"{resp.status} Server Error: {resp.reason} for url: {url}")

        _emit_streaming_heartbeat()
        last_hb = time.monotonic()

        chunk_timeout = base_timeout
        overall_deadline = t_start + max(base_timeout * 3.0, 2700.0) if base_timeout >= 120.0 else t_start + base_timeout * 2.0
        sock_after = getattr(conn, "sock", None)
        if sock_after is not None:
            try:
                sock_after.settimeout(chunk_timeout)
            except Exception:
                pass

        role = "assistant"
        content_parts: List[str] = []
        thinking_parts: List[str] = []
        tool_calls: List[Any] = []
        done = False
        done_reason: Optional[str] = None
        prompt_eval_count = 0
        eval_count = 0

        while True:
            if eff_event is not None and eff_event.is_set():
                _abort_conn()
                raise _OllamaAbortedError("Turn cancelled during Ollama stream")

            fp = getattr(resp, "fp", None)
            has_buf = bool(fp is not None and hasattr(fp, "peek") and fp.peek(1))
            if not has_buf:
                now = time.monotonic()
                chunk_deadline = min(now + chunk_timeout, overall_deadline)
                _await_sock_readable(getattr(conn, "sock", None), chunk_deadline)

            raw_line = resp.readline()
            if not raw_line:
                break
            line_str = raw_line.decode("utf-8", errors="replace").strip()
            if not line_str:
                continue

            chunk = json.loads(line_str)
            if isinstance(chunk, dict) and chunk.get("error"):
                raise RuntimeError(f"Ollama API error: {chunk.get('error')}")

            msg = chunk.get("message") or {}
            if isinstance(msg, dict):
                if msg.get("role"):
                    role = str(msg["role"])
                c_piece = msg.get("content")
                if c_piece:
                    content_parts.append(str(c_piece))
                t_piece = msg.get("thinking") or msg.get("reasoning") or msg.get("reasoning_content")
                if t_piece:
                    thinking_parts.append(str(t_piece))
                tcs = msg.get("tool_calls")
                if isinstance(tcs, list) and tcs:
                    tool_calls.extend(tcs)

            if chunk.get("prompt_eval_count"):
                prompt_eval_count = int(chunk.get("prompt_eval_count") or 0)
            if chunk.get("eval_count"):
                eval_count = int(chunk.get("eval_count") or 0)

            now = time.monotonic()
            if now - last_hb >= 4.0:
                _emit_streaming_heartbeat()
                last_hb = now

            if chunk.get("done"):
                done = True
                done_reason = chunk.get("done_reason")
                break

        msg_out: Dict[str, Any] = {
            "role": role,
            "content": "".join(content_parts),
        }
        if thinking_parts:
            msg_out["thinking"] = "".join(thinking_parts)
        if tool_calls:
            msg_out["tool_calls"] = tool_calls

        return {
            "message": msg_out,
            "done": done,
            "done_reason": done_reason,
            "prompt_eval_count": prompt_eval_count,
            "eval_count": eval_count,
        }
    except _OllamaAbortedError:
        raise
    except (TimeoutError, socket.timeout, requests.Timeout) as exc:
        if eff_event is not None and eff_event.is_set():
            raise _OllamaAbortedError("Ollama stream aborted by user/new turn") from exc
        if isinstance(exc, requests.Timeout):
            raise
        raise requests.Timeout(str(exc)) from exc
    except (OSError, http.client.HTTPException) as exc:
        if eff_event is not None and eff_event.is_set():
            raise _OllamaAbortedError("Ollama stream aborted by user/new turn") from exc
        if "timed out" in str(exc).lower() or "timeout" in str(exc).lower():
            raise requests.Timeout(str(exc)) from exc
        raise requests.ConnectionError(str(exc)) from exc
    finally:
        if hook_registered and eff_event is not None:
            try:
                from hecos.core.agent.turn_control import unregister_abort_hook
                unregister_abort_hook(eff_event, _abort_conn)
            except Exception:
                pass
        try:
            conn.close()
        except Exception:
            pass


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
    }
    if "think" in ollama_body_v1 and ollama_body_v1.get("think") is not None:
        native_body["think"] = ollama_body_v1["think"]

    # Pass options (num_ctx, num_gpu, num_predict, repeat_penalty, temperature, top_p) and promote keep_alive
    native_opts = dict(ollama_body_v1.get("options") or {})
    if "temperature" in ollama_body_v1 and "temperature" not in native_opts:
        native_opts["temperature"] = ollama_body_v1["temperature"]
    if "top_p" in ollama_body_v1 and "top_p" not in native_opts:
        native_opts["top_p"] = ollama_body_v1["top_p"]
    if "keep_alive" in native_opts:
        native_body["keep_alive"] = native_opts.pop("keep_alive")
    if native_opts:
        native_body["options"] = native_opts

    # Tools are not passed since think=False is for fast/no-reasoning responses
    if ollama_body_v1.get("tools"):
        native_body["tools"] = ollama_body_v1["tools"]

    zlog_debug("LiteLLM", f"[OLLAMA-DIRECT] /api/chat (streaming NDJSON) with think={ollama_body_v1.get('think')} model={native_body['model']}")
    native_data = _post_ollama_chat_stream_cancellable(
        api_chat_url,
        native_body,
        timeout=float(params.get("timeout", 900) or 900),
    )

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


def _evict_other_resident_models(ollama_base: str, target_model: str) -> List[str]:
    """
    Unload any OTHER Ollama model currently pinned in VRAM (e.g. from keep_alive=120m)
    before running inference with `target_model`. Prevents Ollama's scheduler from
    deadlocking behind a 17+ GB model when switching presets.
    """
    evicted: List[str] = []
    base = ollama_base.replace("localhost", "127.0.0.1") if "localhost" in ollama_base else ollama_base
    target_clean = str(target_model or "").replace("ollama/", "", 1).strip()
    target_with_latest = f"{target_clean}:latest" if target_clean and ":" not in target_clean else target_clean
    if not target_clean:
        return evicted

    try:
        ps_resp = requests.get(f"{base}/api/ps", timeout=1.5)
        if ps_resp.status_code != 200:
            return evicted
        models = ps_resp.json().get("models", []) or []
    except Exception:
        return evicted

    for pm in models:
        pm_name = str(pm.get("name") or pm.get("model") or "").strip()
        if not pm_name:
            continue
        pm_with_latest = f"{pm_name}:latest" if ":" not in pm_name else pm_name
        if pm_name in (target_clean, target_with_latest) or pm_with_latest in (target_clean, target_with_latest):
            continue
        try:
            zlog_info("LiteLLM", f"[OLLAMA-DIRECT] Swapping model: unloading '{pm_name}' before '{target_clean}'...")
            requests.post(
                f"{base}/api/generate",
                json={"model": pm_name, "prompt": "", "keep_alive": 0, "stream": False},
                timeout=3.0,
            )
            evicted.append(pm_name)
        except Exception as _ue:
            zlog_debug("LiteLLM", f"[OLLAMA-DIRECT] Non-fatal unload error for '{pm_name}': {_ue}")
    return evicted


def execute_ollama_direct(params: Dict[str, Any], stream: bool = False) -> Any:
    """
    Directly invokes Ollama's /v1/chat/completions endpoint (or /api/chat when think=False).
    Bypasses LiteLLM to preserve reasoning fields, avoid dropped tools,
    and accurately record GPU residency metrics.
    """
    ollama_base = params.get("api_base", "http://localhost:11434").rstrip("/")
    if "localhost" in ollama_base:
        ollama_base = ollama_base.replace("localhost", "127.0.0.1")
    ollama_url = f"{ollama_base}/v1/chat/completions"

    has_native_tools = bool(params.get("tools"))
    # Translate LiteLLM params to OpenAI format for Ollama
    target_model = params["model"].replace("ollama/", "", 1)
    ollama_body: Dict[str, Any] = {
        "model": target_model,
        "messages": _normalize_messages_for_ollama(params["messages"], has_native_tools),
        "temperature": params.get("temperature", 0.7),
        "top_p": params.get("top_p", 0.9),
        "stream": False,
    }

    _evict_other_resident_models(ollama_base, target_model)

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

    # Route to /api/chat when think=False OR when runner options (num_ctx, num_gpu, etc.) are present:
    # Ollama's OpenAI-compat /v1/chat/completions ignores `options` (like num_ctx=12288), causing
    # models with large default GGUF context (e.g. Qwen 3.8 262144 ctx) to evict the pre-warmed
    # runner and crash CUDA with a 16+ GB KV cache allocation.
    use_api_chat = (ollama_body.get("think") is False) or bool(ollama_body.get("options"))
    try:
        if use_api_chat:
            zlog_info("LiteLLM", f"[OLLAMA-DIRECT] Routing to native /api/chat (options={list((ollama_body.get('options') or {}).keys())}, think={ollama_body.get('think')})")
            data = _call_api_chat(ollama_base, ollama_body, params)
        else:
            zlog_debug("LiteLLM", f"[OLLAMA-DIRECT] POST {ollama_url} model={ollama_body['model']}")
            data = _post_json_cancellable(
                ollama_url,
                ollama_body,
                timeout=float(params.get("timeout", 900) or 900),
            )
    except _OllamaAbortedError as abort_exc:
        zlog_info("LiteLLM", f"[OLLAMA-DIRECT] {abort_exc}")
        return "⛔ Generation aborted."

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
            except _OllamaAbortedError as _abort_err2:
                zlog_info("LiteLLM", f"[OLLAMA-DIRECT] Retry aborted: {_abort_err2}")
                return "⛔ Generation aborted."
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
