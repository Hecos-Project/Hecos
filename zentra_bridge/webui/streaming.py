"""
MODULE: zentra_bridge/webui/streaming.py
DESCRIPTION: Handles SSE chunked streaming for Open WebUI.
             - Strips <think> tags from model output.
             - Intercepts native JSON tool-calls from the LLM,
               dispatches them to the local plugin executor,
               and re-feeds results back to LiteLLM for a second-pass stream.
"""

import json
import logging
import re
import time
from typing import Generator, List, Optional

bridge_logger = logging.getLogger("WebUI_Bridge")


# ---------------------------------------------------------------------------
# SSE packet factories
# ---------------------------------------------------------------------------

def _make_chunk(content: str, finish: Optional[str] = None) -> str:
    """Returns a single SSE ``data: ...`` line for a text delta."""
    payload = {
        "id":      f"chatcmpl-{int(time.time())}",
        "object":  "chat.completion.chunk",
        "created": int(time.time()),
        "model":   "zentra-local",
        "choices": [{
            "index":         0,
            "delta":         {"content": content} if content else {},
            "finish_reason": finish,
        }],
    }
    return f"data: {json.dumps(payload)}\n\n"


def _make_wake_chunk() -> str:
    """Empty first chunk that wakes Open WebUI's streaming renderer."""
    return _make_chunk("")


def _make_stop_chunk() -> str:
    return _make_chunk("", finish="stop")


# ---------------------------------------------------------------------------
# Core streaming logic
# ---------------------------------------------------------------------------

def stream_response(
    system_prompt: str,
    user_input:    str,
    backend_cfg:   dict,
    llm_config:    dict,
    tool_schemas:  list,
    remove_think:  bool,
    delay_ms:      float,
) -> Generator[str, None, None]:
    """
    Drives the full streaming loop for Open WebUI.  When the LLM returns a
    tool_call we transparently:
      1. Execute the local Zentra plugin.
      2. Insert the tool result as an assistant/tool message pair.
      3. Stream the final LLM answer as SSE.

    Yields:
        SSE strings ready to be yielded directly by the pipe handler.

    Returns:
        (via early return) the accumulated full response text as the *last*
        value sent through a side-channel — callers should capture
        ``testo_completo`` from the generator's ``send`` protocol.
        Instead, this generator returns nothing; the caller is responsible
        for memory saving after draining the generator.
    """
    try:
        from core.llm import client as llm_client
    except ImportError as exc:
        bridge_logger.error(f"[STREAM] LLM client import error: {exc}")
        yield f"data: {json.dumps({'error': {'message': 'LLM client unavailable', 'type': 'internal_error'}})}\n\n"
        return

    try:
        from zentra_bridge.webui.tools import execute_tool_call
    except ImportError:
        execute_tool_call = None  # tool calling disabled

    yield _make_wake_chunk()

    # Build the initial message list for the LLM
    messages: List[dict] = [
        {"role": "system",  "content": system_prompt},
        {"role": "user",    "content": user_input},
    ]

    # We allow at most 3 tool-call rounds to prevent infinite loops
    max_tool_rounds = 3
    testo_completo  = ""

    for _round in range(max_tool_rounds + 1):
        is_last_round = (_round == max_tool_rounds)

        # Pass tools only if we haven't exhausted rounds
        active_tools = (tool_schemas or None) if (not is_last_round and execute_tool_call) else None

        stream_gen = llm_client.generate(
            system_prompt  = system_prompt,
            user_message   = user_input,
            config_or_subconfig = backend_cfg,
            llm_config     = llm_config,
            tools          = active_tools,
            stream         = True,
        )

        if not stream_gen or isinstance(stream_gen, str):
            err = stream_gen if isinstance(stream_gen, str) else "Unknown LLM error"
            bridge_logger.error(f"[STREAM] Generation failed: {err}")
            yield f"data: {json.dumps({'error': {'message': err, 'type': 'api_error'}})}\n\n"
            return

        # ---------------------------------------------------------------
        # Accumulate the raw stream. We need to detect tool_calls which
        # LiteLLM surfaces only when a chunk.choices[0].delta.tool_calls
        # field appears (non-streaming native) OR when the finish_reason
        # is "tool_calls".
        # ---------------------------------------------------------------
        accumulated_tool_calls: dict = {}  # index -> {id, name, arguments}
        current_text = ""
        finish_reason = None

        for chunk in stream_gen:
            try:
                if not (hasattr(chunk, "choices") and chunk.choices):
                    continue

                choice = chunk.choices[0]
                delta  = getattr(choice, "delta", None)
                finish_reason = getattr(choice, "finish_reason", None)

                # Handle content delta
                content = getattr(delta, "content", "") or ""
                if content:
                    if remove_think:
                        content = re.sub(r"</?think>", "", content)
                    if delay_ms > 0:
                        time.sleep(delay_ms)
                    current_text  += content
                    testo_completo += content
                    yield _make_chunk(content)

                # Handle streaming tool_call deltas (OpenAI-style)
                tool_call_deltas = getattr(delta, "tool_calls", None) or []
                for tc_delta in tool_call_deltas:
                    idx = tc_delta.index if hasattr(tc_delta, "index") else 0
                    if idx not in accumulated_tool_calls:
                        accumulated_tool_calls[idx] = {
                            "id":        getattr(tc_delta, "id", "") or "",
                            "name":      "",
                            "arguments": "",
                        }
                    fn = getattr(tc_delta, "function", None)
                    if fn:
                        accumulated_tool_calls[idx]["name"]      += getattr(fn, "name",      "") or ""
                        accumulated_tool_calls[idx]["arguments"] += getattr(fn, "arguments", "") or ""

            except Exception as exc:
                bridge_logger.error(f"[STREAM] Chunk error: {exc}")
                continue

        # ---------------------------------------------------------------
        # Did the model request tool calls?
        # ---------------------------------------------------------------
        if accumulated_tool_calls and execute_tool_call and not is_last_round:
            bridge_logger.info(f"[STREAM] Round {_round}: {len(accumulated_tool_calls)} tool call(s) requested.")

            # Append the assistant's tool-use turn
            tool_calls_schema = []
            for idx, tc in sorted(accumulated_tool_calls.items()):
                tool_calls_schema.append({
                    "id":   tc["id"] or f"call_{idx}",
                    "type": "function",
                    "function": {
                        "name":      tc["name"],
                        "arguments": tc["arguments"],
                    },
                })

            messages.append({
                "role":       "assistant",
                "content":    None,
                "tool_calls": tool_calls_schema,
            })

            # Execute each tool and append results
            for tc in tool_calls_schema:
                fn_name = tc["function"]["name"]
                try:
                    args = json.loads(tc["function"].get("arguments", "{}"))
                except json.JSONDecodeError:
                    args = {}

                bridge_logger.info(f"[TOOLS] Executing: {fn_name}({args})")
                result_str = execute_tool_call(fn_name, args)

                messages.append({
                    "role":         "tool",
                    "tool_call_id": tc["id"],
                    "name":         fn_name,
                    "content":      result_str,
                })

            # Use the updated messages for the next round; re-extract user_input
            # from messages so generate() receives the right history.
            # We rebuild system_prompt + user_input from the messages list.
            # Since client.generate() rebuilds messages internally, we need
            # to pass the full conversation via the user_message workaround:
            # we will call litellm directly with messages (see _stream_with_messages below).
            user_input = _flatten_messages_for_client(messages)
            # Loop for next round
            continue

        # No tool calls — we are done streaming
        break

    # Send stop chunk
    yield _make_stop_chunk()
    yield "data: [DONE]\n\n"

    # Expose the full assembled text for the caller via a final sentinel
    # (streaming generators can't easily return values; we use a convention
    #  where the caller collects everything and filters out the sentinel)
    yield f"__ZENTRA_FULL_TEXT__{testo_completo}"


def _flatten_messages_for_client(messages: List[dict]) -> str:
    """
    Converts a full message list into a single string so that client.generate()
    can receive the conversation history as a single user_message.
    This is a simple workaround until client.generate() supports full message lists.
    """
    parts = []
    for m in messages:
        role    = m.get("role", "user")
        content = m.get("content") or ""
        if role == "system":
            continue  # system prompt is handled separately
        if role == "tool":
            parts.append(f"[TOOL RESULT: {m.get('name','')}]\n{content}")
        elif role == "assistant":
            if content:
                parts.append(f"[ASSISTANT]\n{content}")
        else:
            parts.append(f"[USER]\n{content}")
    return "\n\n".join(parts)
