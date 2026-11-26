import re
import time
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    from hecos.core.logging import logger
except Exception:
    import logging
    logger = logging.getLogger("hecos.legacy_tag_parser")


_MODULE_CALL_PREFIX_RE = re.compile(
    r'(?<![A-Za-z0-9_])([A-Z][A-Z0-9_]{1,30})__([a-z][a-z0-9_]{1,48})\s*\('
)


def _find_closing_paren(text: str, open_idx: int) -> int:
    """Finds the matching ')' for '(' at open_idx, respecting quoted strings and nested parens."""
    depth = 0
    in_quote: Optional[str] = None
    escaped = False
    n = len(text)
    for i in range(open_idx, n):
        ch = text[i]
        if escaped:
            escaped = False
            continue
        if ch == "\\" and in_quote is not None:
            escaped = True
            continue
        if in_quote is not None:
            if ch == in_quote:
                in_quote = None
            continue
        if ch in ('"', "'"):
            in_quote = ch
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return i
    return -1


def extract_module_call_spans(
    text: str,
    allowed_modules: Optional[Set[str]] = None,
) -> List[Tuple[int, int, str, str, str]]:
    """
    Extracts inline `MODULE__method(args)` text calls with balanced parentheses.
    Returns list of `(span_start, span_end, module_upper, method_name, raw_args)`.
    """
    if not isinstance(text, str) or "__" not in text:
        return []

    found: List[Tuple[int, int, str, str, str]] = []
    pos_cursor = 0
    for m in _MODULE_CALL_PREFIX_RE.finditer(text):
        if m.start() < pos_cursor:
            continue
        mod_upper = m.group(1).upper()
        if allowed_modules and mod_upper not in allowed_modules and not mod_upper.startswith("MCP_"):
            continue
        open_idx = m.end() - 1
        close_idx = _find_closing_paren(text, open_idx)
        if close_idx < 0:
            continue
        span_start = m.start()
        span_end = close_idx + 1
        # Include optional enclosing single/triple backticks for clean stripping
        if span_start > 0 and span_end < len(text) and text[span_start - 1] == "`" and text[span_end] == "`":
            span_start -= 1
            span_end += 1
        raw_args = text[open_idx + 1 : close_idx].strip()
        found.append((span_start, span_end, mod_upper, m.group(2), raw_args))
        pos_cursor = span_end
    return found


def strip_module_call_syntax(text: str, allowed_modules: Optional[Set[str]] = None) -> str:
    """Removes inline `MODULE__method(...)` invocations (and leftover empty code fences) from text."""
    if not isinstance(text, str) or "__" not in text:
        return text or ""
    spans = extract_module_call_spans(text, allowed_modules=allowed_modules)
    if not spans:
        return text
    out_parts: List[str] = []
    last = 0
    for s, e, _mod, _meth, _args in spans:
        out_parts.append(text[last:s])
        last = e
    out_parts.append(text[last:])
    cleaned = "".join(out_parts)
    cleaned = re.sub(r'```(?:python|json|tool_code)?\s*```', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    return cleaned.strip()


def _mask_code_spans(text: str) -> str:
    """Replace fenced code blocks and inline code spans with neutral spaces so code syntax is never parsed as legacy tags."""
    if not text:
        return ""
    masked = re.sub(r'```[\s\S]*?```', lambda m: ' ' * len(m.group(0)), text)
    masked = re.sub(r'`[^`\r\n]+`', lambda m: ' ' * len(m.group(0)), masked)
    return masked


_TOOL_RESPONSE_BLOCK_RE = re.compile(
    r"<tool_response>[\s\S]*?(?:</tool_response>|$)",
    re.IGNORECASE,
)

_NON_EMPTY_SIMPLE_TAGS = frozenset({
    "EXECUTOR", "SYSTEM", "CORE", "MEMORY", "NETSEARCH", "MCP_BRIDGE",
    "INFO", "DEBUG", "WARNING", "WARN", "ERROR", "CRITICAL", "TRACE",
    "TOOL", "STATUS", "OK", "FAILED", "HEALTH", "AUTO", "WEB",
})


class LegacyTagParser:
    """
    Extracts legacy bracket tags (e.g., [TOOL:ACTION] or [TOOL]), slash commands,
    and inline `MODULE__method(...)` text calls emitted by local models (e.g. Gemma 4).
    """
    
    @staticmethod
    def parse(base_text: str, raw_response: Any, tags_found: list) -> None:
        """
        Extracts tags and mutates the tags_found list.
        """
        sanitized_base = _TOOL_RESPONSE_BLOCK_RE.sub("", base_text) if isinstance(base_text, str) else ""
        sanitized_raw = _TOOL_RESPONSE_BLOCK_RE.sub("", raw_response) if isinstance(raw_response, str) else ""
        masked_text = _mask_code_spans(sanitized_base)
        masked_raw = _mask_code_spans(sanitized_raw)

        bracket_spans: List[Tuple[int, int]] = []
        # Match standard [TOOL:ACTION] (requiring identifier starting with a letter), ignoring double-bracket UI tokens, URIs & code blocks
        _uri_schemes = frozenset({"IMG", "HSEARCH", "HMEDIA", "HTTP", "HTTPS", "FTP", "FILE", "WS", "WSS", "MAILTO", "TEL", "DATA"})
        for m in re.finditer(r'(?<!\[)\[([A-Za-z][A-Za-z0-9_]*):([^\[\]]*?)\](?!\])', masked_text, flags=re.DOTALL):
            tag, action = m.group(1), m.group(2)
            if tag.upper() in _uri_schemes or action.lstrip().startswith("//"):
                continue
            bracket_spans.append((m.start(), m.end()))
            tags_found.append((tag.lower(), action.strip(), "standard", None))
        
        # Match simple [TOOL] (requiring identifier starting with a letter so [0], [1] never trigger module errors)
        if masked_raw:
            matches_simple = re.findall(r'(?<!\[)\[([A-Za-z][A-Za-z0-9_]*)\](?!\])', masked_raw)
            for tag in matches_simple:
                if tag.upper() in _NON_EMPTY_SIMPLE_TAGS:
                    continue
                if not any(t[0] == tag.lower() for t in tags_found):
                    tags_found.append((tag.lower(), "", "simple", None))

        # Match Slash Commands (e.g., /img, /search, /pdf) emitted by the LLM on their own line
        # (including bulleted or numbered lists such as "1. /img ..." or "- /img ..."), outside code blocks.
        # Note: require whitespace or end-of-line after the command token so URL paths like
        # /api/images/... or /snapshots/... are never mistaken for slash commands.
        if masked_text:
            slash_matches = re.findall(
                r'^\s*(?:(?:\d{1,2}[\.\)]|[-*•])\s+)?(/[a-zA-Z0-9_]+(?:\s+[^\r\n]*)?)(?:\r?\n|$)',
                masked_text,
                flags=re.MULTILINE,
            )
            seen_cmds = set()
            img_cmd_count = 0
            for cmd in slash_matches:
                cmd_clean = cmd.strip()
                if not cmd_clean or cmd_clean in seen_cmds:
                    continue
                seen_cmds.add(cmd_clean)
                
                # Check for image commands (/img, /image, /photo, /foto)
                is_img = cmd_clean.lower().startswith(("/img", "/image", "/photo", "/foto"))
                if is_img:
                    img_cmd_count += 1
                    # Safety upper bound for single response (tool_dispatcher will enforce precise limit)
                    if img_cmd_count > 20:
                        continue
                tags_found.append(("direct_command", cmd_clean, "slash", None))
                
            # Fallback: some LLMs might emit HTML tags like <img description> or <img prompt="description">
            if img_cmd_count == 0:
                html_img_matches = re.findall(r'<img\s+([^>]+)>', base_text, flags=re.IGNORECASE)
                for img_desc in html_img_matches:
                    # Ignore actual HTML tags with URLs/paths in src (e.g. <img src="/api/images/...">)
                    if re.search(r'src\s*=\s*["\'](?:/api/|http|data:|file:)', img_desc, re.IGNORECASE):
                        continue
                    clean_desc = re.sub(r'^(?:prompt|alt|title)\s*=\s*["\'](.*?)["\']', r'\1', img_desc.strip(), flags=re.IGNORECASE)
                    cmd_clean = f"/img {clean_desc.strip()}"
                    if cmd_clean not in seen_cmds:
                        seen_cmds.add(cmd_clean)
                        img_cmd_count += 1
                        tags_found.append(("direct_command", cmd_clean, "slash", None))
                        if img_cmd_count >= 20:
                            break

            # Match bare/backticked `MODULE__method(args...)` emitted by text-only models (e.g. Gemma 4)
            allowed_mods: Optional[Set[str]] = None
            try:
                from hecos.core.system import module_loader
                active = module_loader.get_active_tags()
                if active:
                    allowed_mods = {str(t).upper() for t in active} | {"SYSTEM", "CORE"}
            except Exception:
                allowed_mods = None

            spans = extract_module_call_spans(sanitized_base, allowed_modules=allowed_mods)
            if spans:
                from hecos.core.processing.tool_invoker import parse_call_kwargs
                seen_calls: Set[Tuple[str, str, str]] = set()
                for s, e, mod_upper, method_name, raw_args in spans:
                    # Skip if already inside a [TAG: ...] bracket span
                    if any(bs <= s and e <= be for bs, be in bracket_spans):
                        continue
                    dedup_key = (mod_upper, method_name, raw_args)
                    if dedup_key in seen_calls:
                        continue
                    seen_calls.add(dedup_key)
                    parsed_args = parse_call_kwargs(raw_args)
                    call_id = f"text_call_{int(time.time())}_{len(tags_found) + 1}"
                    tags_found.append((mod_upper.lower(), parsed_args, "function_call", method_name, call_id))
                    logger.info(
                        f"[PROCESSOR] Parsed text-mode function call: {mod_upper}__{method_name}({raw_args[:120]})"
                    )
