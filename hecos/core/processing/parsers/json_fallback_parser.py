import json
import re
import time
from typing import Any, List, Optional, Tuple
from hecos.core.logging import logger


# Matches qualified module tool names emitted by Hecos schemas: MODULE__method
_QUALIFIED_TOOL_NAME_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_]*)__([A-Za-z_][A-Za-z0-9_]*)$")


def _extract_tool_entries_from_dict(
    parsed_json: dict,
    call_counter: List[int],
) -> Tuple[List[Tuple[str, Any, str, Optional[str], str]], bool]:
    """
    Extracts structured tool invocations from a parsed JSON dict.
    Supports:
      1. {"function": {"name": "TAG__method", "arguments|parameters": ...}}
      2. {"name": "TAG__method", "arguments|parameters": ...}  (Qwen/Ollama raw style)
      3. {"tool_calls": [{"function": {"name": "TAG__method", "arguments": ...}}, ...]}
    Returns (extracted_calls, matched_tool_shape).
    """
    extracted: List[Tuple[str, Any, str, Optional[str], str]] = []
    ts = int(time.time())

    def _next_id(explicit_id: Optional[str] = None) -> str:
        if explicit_id:
            return str(explicit_id)
        call_counter[0] += 1
        return f"call_{ts}_{call_counter[0]}"

    def _normalize_args(raw_args: Any) -> Any:
        if isinstance(raw_args, str):
            stripped = raw_args.strip()
            if stripped.startswith("{") and stripped.endswith("}"):
                try:
                    return json.loads(stripped)
                except Exception:
                    return raw_args
        return {} if raw_args is None else raw_args

    # 1. OpenAI/tool wrapper: {"function": {"name": "...", "arguments": ...}}
    if "function" in parsed_json and isinstance(parsed_json["function"], dict):
        f_obj = parsed_json["function"]
        f_name = str(f_obj.get("name") or "").strip()
        m = _QUALIFIED_TOOL_NAME_RE.match(f_name)
        if m:
            f_args = _normalize_args(f_obj.get("parameters", f_obj.get("arguments", {})))
            extracted.append((m.group(1).lower(), f_args, "function_call", m.group(2), _next_id()))
            return extracted, True

    # 2. Qwen / Ollama raw format: {"name": "TAG__method", "arguments": {...}}
    if isinstance(parsed_json.get("name"), str) and (
        "arguments" in parsed_json or "parameters" in parsed_json
    ):
        f_name = parsed_json["name"].strip()
        m = _QUALIFIED_TOOL_NAME_RE.match(f_name)
        if m:
            f_args = _normalize_args(parsed_json.get("parameters", parsed_json.get("arguments", {})))
            extracted.append((m.group(1).lower(), f_args, "function_call", m.group(2), _next_id()))
            return extracted, True

    # 3. List wrapper: {"tool_calls": [...]}
    if "tool_calls" in parsed_json and isinstance(parsed_json["tool_calls"], list):
        matched_any = False
        for tc in parsed_json["tool_calls"]:
            if not isinstance(tc, dict):
                continue
            f_obj = tc.get("function") if isinstance(tc.get("function"), dict) else tc
            f_name = str(f_obj.get("name") or "").strip()
            m = _QUALIFIED_TOOL_NAME_RE.match(f_name)
            if m:
                f_args = _normalize_args(f_obj.get("parameters", f_obj.get("arguments", {})))
                extracted.append(
                    (m.group(1).lower(), f_args, "function_call", m.group(2), _next_id(tc.get("id")))
                )
                matched_any = True
        if matched_any:
            return extracted, True

    return extracted, False


def _expand_span_to_wrapper(text: str, start: int, end: int) -> Tuple[int, int]:
    """Expands a JSON span [start, end) to include any surrounding ```json ...``` or <tool_call>...</tool_call> wrapper."""
    prefix = text[:start]
    suffix = text[end:]

    m_tc_pre = re.search(r"<tool_call>\s*$", prefix, re.IGNORECASE)
    m_tc_suf = re.match(r"^\s*</tool_call>", suffix, re.IGNORECASE)
    if m_tc_pre and m_tc_suf:
        return m_tc_pre.start(), end + m_tc_suf.end()

    m_fence_pre = re.search(r"```(?:json)?[ \t]*\r?\n[ \t]*$", prefix, re.IGNORECASE)
    m_fence_suf = re.match(r"^[ \t]*\r?\n?[ \t]*```", suffix)
    if m_fence_pre and m_fence_suf:
        return m_fence_pre.start(), end + m_fence_suf.end()

    return start, end


class JsonFallbackParser:
    """
    Parses fallback JSON outputs from models (e.g. Ollama models that fail to use
    native tool calls and return raw JSON text instead — single, wrapped, or multiple inline).
    """

    @staticmethod
    def parse(base_text: str, tags_found: list, think_block: Optional[str]) -> Tuple[str, Optional[str]]:
        """
        Parses JSON tool calls and response/thought wrappers from model text, appends
        valid MODULE__method tool calls to tags_found, and strips executed JSON call blocks.
        """
        if not base_text or not isinstance(base_text, str):
            return base_text, think_block

        call_counter = [0]
        raw_stripped = base_text.strip()

        # Fast-path: whole output is a single standalone JSON dict wrapper
        if raw_stripped.startswith("{") and raw_stripped.endswith("}"):
            try:
                parsed_json = json.loads(raw_stripped)
                if isinstance(parsed_json, dict):
                    extracted, matched = _extract_tool_entries_from_dict(parsed_json, call_counter)
                    if matched:
                        tags_found.extend(extracted)
                        logger.info(
                            f"[PROCESSOR] Intercepted standalone JSON tool call(s): "
                            f"{[f'{t[0].upper()}__{t[3]}' for t in extracted]}"
                        )
                        return "", think_block

                    if "response" in parsed_json or "thought" in parsed_json:
                        resp = parsed_json.get("response")
                        thought_val = parsed_json.get("thought", None)

                        if thought_val is not None:
                            if isinstance(thought_val, str):
                                think_block = thought_val.strip()
                            elif isinstance(thought_val, dict):
                                think_block = thought_val.get("reasoning", "").strip() or str(thought_val).strip()

                        if isinstance(resp, dict) and "text" in resp:
                            base_text = resp["text"]
                        elif isinstance(resp, str):
                            base_text = resp
                        elif resp is not None:
                            base_text = str(resp)
                        elif thought_val is not None and not resp:
                            base_text = ""

                        logger.info("[PROCESSOR] Intercepted raw JSON thought/response block.")
                        return base_text, think_block

                    if "text" in parsed_json and isinstance(parsed_json["text"], str) and len(parsed_json) <= 5:
                        base_text = parsed_json["text"]
                        logger.info("[PROCESSOR] Intercepted raw JSON {text:...} response block.")
                        return base_text, think_block
            except Exception:
                pass

        # Inline / multi-block scan: extract one or more JSON tool calls embedded in markdown/prose
        decoder = json.JSONDecoder()
        removal_spans: List[Tuple[int, int]] = []
        pos = 0
        text_len = len(base_text)

        while pos < text_len:
            brace_idx = base_text.find("{", pos)
            if brace_idx == -1:
                break
            try:
                obj, end_idx = decoder.raw_decode(base_text, brace_idx)
            except Exception:
                pos = brace_idx + 1
                continue

            if isinstance(obj, dict):
                extracted, matched = _extract_tool_entries_from_dict(obj, call_counter)
                if matched:
                    tags_found.extend(extracted)
                    span_start, span_end = _expand_span_to_wrapper(base_text, brace_idx, end_idx)
                    removal_spans.append((span_start, span_end))
                    pos = max(end_idx, span_end)
                    continue

            pos = brace_idx + 1

        if removal_spans:
            merged_spans: List[List[int]] = []
            for s_start, s_end in sorted(removal_spans):
                if merged_spans and s_start <= merged_spans[-1][1]:
                    merged_spans[-1][1] = max(merged_spans[-1][1], s_end)
                else:
                    merged_spans.append([s_start, s_end])

            parts: List[str] = []
            cursor = 0
            for s_start, s_end in merged_spans:
                parts.append(base_text[cursor:s_start])
                cursor = s_end
            parts.append(base_text[cursor:])

            cleaned = re.sub(r"\n{3,}", "\n\n", "".join(parts)).strip()
            logger.info(
                f"[PROCESSOR] Intercepted {len(tags_found)} inline JSON tool call(s): "
                f"{[f'{t[0].upper()}__{t[3]}' for t in tags_found]}"
            )
            return cleaned, think_block

        return base_text, think_block
