"""
hecos/core/agent/context_budget.py
Coding-mode detection and context window budgeting/compaction for multi-turn agent loops.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def _is_coding_loop_active(cfg: Optional[Dict[str, Any]]) -> bool:
    """Detect whether the current turn runs in dedicated coding mode (Hecos Coder / Executor write tools)."""
    if not isinstance(cfg, dict):
        return False
    ai_cfg = cfg.get("ai", {}) if isinstance(cfg.get("ai"), dict) else {}
    persona_cfg = cfg.get("persona", {}) if isinstance(cfg.get("persona"), dict) else {}
    persona = str(
        ai_cfg.get("active_personality")
        or ai_cfg.get("personality")
        or persona_cfg.get("soul_file")
        or cfg.get("personality_name", "")
        or ""
    ).lower()
    if "hecos_coder" in persona:
        return True
    pctrl = cfg.get("payload_control", {}) if isinstance(cfg.get("payload_control"), dict) else {}
    selected = pctrl.get("selected_tools") or []
    if isinstance(selected, list):
        coding_markers = {"EXECUTOR__*", "EXECUTOR__write_file", "EXECUTOR__patch_file", "EXECUTOR__repo_map"}
        if any(s in coding_markers for s in selected):
            return True
    return False


def compact_agent_context_tool_messages(
    agent_context: List[Dict[str, Any]],
    keep_recent: int = 3,
    min_chars_to_compact: int = 700,
) -> int:
    """
    Compact verbose older `role='tool'` outputs inside `agent_context` while keeping the newest
    `keep_recent` tool outputs verbatim. Preserves first header line and key diagnostics so
    local 16k-context models do not overflow during multi-step coding workflows.
    Returns the number of messages compacted.
    """
    tool_indices = [
        idx for idx, msg in enumerate(agent_context)
        if isinstance(msg, dict) and msg.get("role") == "tool"
    ]
    if len(tool_indices) <= max(1, int(keep_recent)):
        return 0

    cutoff_indices = tool_indices[:-max(1, int(keep_recent))]
    compacted = 0
    important_tokens = (
        "[AUTO-CHECK]", "[WEB-DIAGNOSTIC]", "[AUTO-TEST]", "[HEALTH-CHECK",
        "SYNTAX ERROR", "RUFF", "Traceback", "FAILED", "Ambiguous patch",
    )

    for idx in cutoff_indices:
        msg = agent_context[idx]
        content = msg.get("content")
        if not isinstance(content, str) or len(content) <= min_chars_to_compact:
            continue
        if "[COMPACTED EARLIER OUTPUT" in content:
            continue

        orig_len = len(content)
        lines = [ln.strip() for ln in content.splitlines() if ln.strip()]
        kept: List[str] = []
        if lines:
            kept.append(lines[0][:220])
        for ln in lines[1:]:
            if any(tok in ln for tok in important_tokens):
                kept.append(ln[:200])
                if len(kept) >= 4:
                    break
        summary = "\n".join(kept)
        if len(summary) > 520:
            summary = summary[:520] + "..."
        msg["content"] = (
            f"{summary}\n"
            f"[COMPACTED EARLIER OUTPUT ({msg.get('name') or 'tool'}): {orig_len} chars condensed "
            f"to protect context window; re-read/re-run if exact contents are needed.]"
        )
        compacted += 1

    return compacted


def _resolve_effective_num_ctx(cfg: Optional[Dict[str, Any]]) -> int:
    """Resolve active context window size (tokens) from session/backend config cleanly."""
    default_ctx = 16384
    if not isinstance(cfg, dict):
        return default_ctx
    backend = cfg.get("backend", {})
    if isinstance(backend, dict):
        btype = str(backend.get("type") or "ollama").lower()
        sub = backend.get(btype, {})
        if isinstance(sub, dict) and sub.get("num_ctx"):
            try:
                return max(4096, int(sub["num_ctx"]))
            except (TypeError, ValueError):
                pass
    inf = cfg.get("inference", {})
    if isinstance(inf, dict) and inf.get("num_ctx"):
        try:
            return max(4096, int(inf["num_ctx"]))
        except (TypeError, ValueError):
            pass
    return default_ctx


def enforce_agent_context_budget(
    agent_context: List[Dict[str, Any]],
    cfg: Optional[Dict[str, Any]],
    user_text: str = "",
) -> int:
    """
    Keep multi-step `agent_context` + `user_text` comfortably inside ~70% of `num_ctx`
    so local models do not overflow, stall in KV thrash, or get silently truncated.
    Returns number of compacted/trimmed messages.
    """
    if not agent_context:
        return 0

    num_ctx = _resolve_effective_num_ctx(cfg)
    total_char_cap = max(14000, int(num_ctx * 0.78 * 3.2) - 18000)

    def _context_chars() -> int:
        return len(user_text or "") + sum(len(str(m.get("content") or "")) for m in agent_context)

    if _context_chars() <= total_char_cap:
        return 0

    changed = compact_agent_context_tool_messages(agent_context, keep_recent=2, min_chars_to_compact=260)
    if _context_chars() <= total_char_cap:
        return changed

    asst_indices = [
        i for i, m in enumerate(agent_context)
        if isinstance(m, dict) and m.get("role") == "assistant"
    ]
    for idx in asst_indices[:-1]:
        msg = agent_context[idx]
        content = str(msg.get("content") or "")
        if len(content) <= 400 or "[CONDENSED PRIOR STEP" in content:
            continue
        first_line = next((ln.strip()[:180] for ln in content.splitlines() if ln.strip()), "")
        msg["content"] = f"{first_line}\n[CONDENSED PRIOR STEP ({len(content)} chars) to stay within num_ctx={num_ctx}.]"
        changed += 1
        if _context_chars() <= total_char_cap:
            return changed

    while len(agent_context) > 4 and _context_chars() > total_char_cap:
        removed = agent_context.pop(0)
        if isinstance(removed, dict) and removed.get("role") == "assistant":
            while len(agent_context) > 4 and isinstance(agent_context[0], dict) and agent_context[0].get("role") == "tool":
                agent_context.pop(0)
        changed += 1

    return changed
