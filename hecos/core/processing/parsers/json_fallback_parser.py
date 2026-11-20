import json
import re
import time
from typing import Any, Dict, List, Optional, Tuple
from hecos.core.logging import logger


# Matches qualified module tool names emitted by Hecos schemas: MODULE__method
_QUALIFIED_TOOL_NAME_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_]*)__([A-Za-z_][A-Za-z0-9_]*)$")
_TOOL_CALL_WRAPPER_RE = re.compile(r"<tool_call>\s*([\s\S]*?)\s*</tool_call>", re.IGNORECASE)
_TRUNCATED_TOOL_CALL_RE = re.compile(r"<tool_call>\s*([\s\S]*)$", re.IGNORECASE)
_TRIPLE_QUOTE_RE = re.compile(r'"""([\s\S]*?)"""|\'\'\'([\s\S]*?)\'\'\'')
_JSON_ESCAPE_RE = re.compile(r'\\(u[0-9a-fA-F]{4}|.)', re.DOTALL)
_VALID_JSON_SHORT_ESCAPES = set('"\\/bfnrt')


def _fix_invalid_json_escapes(snippet: str) -> str:
    """Escapes stray backslashes (e.g. Windows paths C:\\Hecos or Python \\d) invalid in JSON strings."""
    def _repl(match: re.Match) -> str:
        tok = match.group(1)
        if len(tok) == 5 and tok[0] == "u":
            return match.group(0)
        if tok in _VALID_JSON_SHORT_ESCAPES:
            return match.group(0)
        return "\\\\" + tok

    return _JSON_ESCAPE_RE.sub(_repl, snippet)


def _convert_triple_quotes_to_json(snippet: str) -> str:
    """Replaces Python triple-quoted values inside pseudo-JSON tool calls with valid JSON strings."""
    def _repl(match: re.Match) -> str:
        body = match.group(1) if match.group(1) is not None else (match.group(2) or "")
        return json.dumps(body)

    return _TRIPLE_QUOTE_RE.sub(_repl, snippet)


def _find_balanced_brace_end(text: str, start_idx: int) -> int:
    """Finds matching '}' for '{' at start_idx, tolerating newlines inside strings."""
    depth = 0
    in_str = False
    escaped = False
    n = len(text)
    for i in range(start_idx, n):
        ch = text[i]
        if escaped:
            escaped = False
            continue
        if ch == "\\" and in_str:
            escaped = True
            continue
        if ch == '"':
            in_str = not in_str
            continue
        if not in_str:
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return i
    return -1


def _decode_pseudo_json_escapes(raw_str: str) -> str:
    """Single-pass JSON escape decoder for fallback write_file recovery."""
    esc_map = {"n": "\n", "r": "\r", "t": "\t", '"': '"', "\\": "\\", "/": "/"}
    return re.sub(r"\\(.)", lambda m: esc_map.get(m.group(1), m.group(0)), raw_str)


def _recover_write_file_payload(snippet: str) -> Optional[Dict[str, Any]]:
    """
    Last-resort recovery for inline `EXECUTOR__write_file` / `run_aider_task` JSON blocks
    that contain unescaped double quotes inside `"content"` (e.g. HTML attributes or Python quotes).
    """
    m_name = re.search(r'"name"\s*:\s*"([A-Za-z][A-Za-z0-9_]*__[A-Za-z_][A-Za-z0-9_]*)"', snippet)
    if not m_name:
        return None
    tool_name = m_name.group(1)
    if tool_name.upper().endswith("__WRITE_FILE"):
        m_fp = re.search(r'"file_path"\s*:\s*"([^"\r\n]+)"', snippet)
        m_content = re.search(
            r'"content"\s*:\s*"([\s\S]*)"\s*(?:,\s*"mode"\s*:\s*"([wa])"\s*)?\}\s*(?:\}|$)',
            snippet,
        )
        if m_fp and m_content:
            decoded = _decode_pseudo_json_escapes(m_content.group(1))
            args: Dict[str, Any] = {"file_path": m_fp.group(1).strip(), "content": decoded}
            if m_content.group(2):
                args["mode"] = m_content.group(2)
            return {"name": tool_name, "arguments": args}
    return None


def _parse_tolerant_json_dict(raw_snippet: str) -> Optional[Dict[str, Any]]:
    """Parses JSON with fallback repairs for literal newlines, triple quotes, and lone backslashes."""
    text = (raw_snippet or "").strip()
    if not text.startswith("{"):
        b = text.find("{")
        if b == -1:
            return None
        text = text[b:]
    for candidate in (
        text,
        _fix_invalid_json_escapes(text),
        _convert_triple_quotes_to_json(text),
        _fix_invalid_json_escapes(_convert_triple_quotes_to_json(text)),
    ):
        try:
            parsed = json.loads(candidate, strict=False)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            continue
    return _recover_write_file_payload(text)


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
                parsed = _parse_tolerant_json_dict(stripped)
                if parsed is not None:
                    return parsed
                try:
                    return json.loads(stripped, strict=False)
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
    def parse_with_diagnostics(
        base_text: str,
        tags_found: list,
        think_block: Optional[str],
    ) -> Tuple[str, Optional[str], List[str]]:
        """
        Parses JSON tool calls (including multiline `<tool_call>` blocks and tolerance repairs)
        and response/thought wrappers from model text.
        Returns `(cleaned_text, think_block, malformed_tool_names)`.
        """
        if not base_text or not isinstance(base_text, str):
            return base_text, think_block, []

        call_counter = [0]
        raw_stripped = base_text.strip()
        malformed_names: List[str] = []

        # Fast-path: whole output is a single standalone JSON dict wrapper
        if raw_stripped.startswith("{") and raw_stripped.endswith("}"):
            parsed_json = _parse_tolerant_json_dict(raw_stripped)
            if isinstance(parsed_json, dict):
                extracted, matched = _extract_tool_entries_from_dict(parsed_json, call_counter)
                if matched:
                    tags_found.extend(extracted)
                    logger.info(
                        f"[PROCESSOR] Intercepted standalone JSON tool call(s): "
                        f"{[f'{t[0].upper()}__{t[3]}' for t in extracted]}"
                    )
                    return "", think_block, []

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
                    return base_text, think_block, []

                if "text" in parsed_json and isinstance(parsed_json["text"], str) and len(parsed_json) <= 5:
                    base_text = parsed_json["text"]
                    logger.info("[PROCESSOR] Intercepted raw JSON {text:...} response block.")
                    return base_text, think_block, []

        removal_spans: List[Tuple[int, int]] = []

        # Pass 1: Explicit <tool_call>...</tool_call> blocks (supports multiline & repair fallbacks)
        for m_tc in _TOOL_CALL_WRAPPER_RE.finditer(base_text):
            inner = m_tc.group(1)
            obj = _parse_tolerant_json_dict(inner)
            extracted_ok = False
            if isinstance(obj, dict):
                extracted, matched = _extract_tool_entries_from_dict(obj, call_counter)
                if matched:
                    tags_found.extend(extracted)
                    extracted_ok = True
            if not extracted_ok:
                m_bad = re.search(r'"name"\s*:\s*"([A-Za-z][A-Za-z0-9_]*__[A-Za-z_][A-Za-z0-9_]*)"', inner)
                bad_name = m_bad.group(1) if m_bad else "unknown_tool_call"
                malformed_names.append(bad_name)
                logger.warning(f"[PROCESSOR] Dropped malformed <tool_call> block for '{bad_name}'.")
            removal_spans.append((m_tc.start(), m_tc.end()))

        # Handle truncated trailing <tool_call> cut off by token limit (no closing </tool_call>)
        last_covered_end = max((e for _, e in removal_spans), default=0)
        m_trunc = _TRUNCATED_TOOL_CALL_RE.search(base_text, pos=last_covered_end)
        if m_trunc:
            inner = m_trunc.group(1)
            m_bad = re.search(r'"name"\s*:\s*"([A-Za-z][A-Za-z0-9_]*__[A-Za-z_][A-Za-z0-9_]*)"', inner)
            bad_name = m_bad.group(1) if m_bad else "truncated_tool_call"
            malformed_names.append(bad_name)
            logger.warning(f"[PROCESSOR] Dropped truncated trailing <tool_call> for '{bad_name}'.")
            removal_spans.append((m_trunc.start(), m_trunc.end()))

        def _inside_removed(idx: int) -> bool:
            return any(s <= idx < e for s, e in removal_spans)

        # Pass 2: Inline / multi-block bare JSON scan (strict=False handles literal newlines in code)
        decoder = json.JSONDecoder(strict=False)
        pos = 0
        text_len = len(base_text)

        while pos < text_len:
            brace_idx = base_text.find("{", pos)
            if brace_idx == -1:
                break
            if _inside_removed(brace_idx):
                covering = [e for s, e in removal_spans if s <= brace_idx < e]
                pos = max(covering) if covering else brace_idx + 1
                continue

            obj = None
            end_idx = -1
            try:
                obj, end_idx = decoder.raw_decode(base_text, brace_idx)
            except Exception:
                preview = base_text[brace_idx : brace_idx + 240]
                if "__" in preview and ('"name"' in preview or '"function"' in preview or '"tool_calls"' in preview):
                    bal_end = _find_balanced_brace_end(base_text, brace_idx)
                    if bal_end > brace_idx:
                        cand_obj = _parse_tolerant_json_dict(base_text[brace_idx : bal_end + 1])
                        if isinstance(cand_obj, dict):
                            obj = cand_obj
                            end_idx = bal_end + 1

            if isinstance(obj, dict) and end_idx > brace_idx:
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
            if tags_found:
                logger.info(
                    f"[PROCESSOR] Intercepted {len(tags_found)} inline JSON tool call(s): "
                    f"{[f'{t[0].upper()}__{t[3]}' for t in tags_found]}"
                )
            return cleaned, think_block, malformed_names

        return base_text, think_block, malformed_names

    @staticmethod
    def parse(base_text: str, tags_found: list, think_block: Optional[str]) -> Tuple[str, Optional[str]]:
        """
        Parses JSON tool calls and response/thought wrappers from model text, appends
        valid MODULE__method tool calls to tags_found, and strips executed JSON call blocks.
        """
        cleaned, updated_think, _malformed = JsonFallbackParser.parse_with_diagnostics(
            base_text, tags_found, think_block
        )
        return cleaned, updated_think
