"""
hecos/core/agent/stagnation_breaker.py
Deterministic stagnation signature builder and repetitive failing loop circuit-breaker.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

_DYNAMIC_TRACE_NOISE_RE = re.compile(
    r"(?:\brun_\d+_[0-9a-f]+\b|\bPID=\d+\b|\b\d+ms\b|\b\d+\.\d+s\b)",
    re.IGNORECASE,
)

_LOOP_FAIL_MARKERS = (
    "exit code: 1",
    "[auto-test] failed",
    "[health-check failed]",
    "http unreachable",
    "path not found:",
    "file not found:",
    "unknown run_id:",
    "syntax error",
    "traceback (most recent",
    "test execution timed out",
)

_LOOP_SUCCESS_MARKERS = (
    "[auto-test] passed",
    "[health-check ok]",
    "exit code: 0",
    "[aider]",
)


def classify_tool_result_for_loop(res: Dict[str, Any]) -> Tuple[str, bool, str]:
    """
    Classify one executed tool result as (outcome_bucket, had_clean_progress, short_diagnostic).
    Used by AgentExecutor's circuit-breaker to stop identical no-progress loops early.
    """
    out = str(res.get("output") or "")
    low = out.lower()
    action = str(res.get("action") or "").lower()

    fail_hits = [tok for tok in _LOOP_FAIL_MARKERS if tok in low]
    is_write = action in {"write_file", "patch_file", "run_aider_task", "move_path", "create_dir"}
    clean_disk_write = (
        ("file verified on disk:" in low or "file patched and verified on disk:" in low or "directory created:" in low)
        and not fail_hits
    )
    aider_ok = action == "run_aider_task" and "failed" not in low and "not installed" not in low

    if fail_hits:
        bucket = "FAIL:" + "|".join(fail_hits[:3])
        diag_line = ""
        for ln in out.splitlines():
            s = ln.strip()
            if any(k in s.lower() for k in (
                "web-diagnostic", "syntax error", "importerror", "modulenotfounderror",
                "health-check failed", "path not found", "unknown run_id", "timed out",
            )):
                diag_line = s[:220]
                break
        if not diag_line and out.strip():
            diag_line = _DYNAMIC_TRACE_NOISE_RE.sub("", out.strip().splitlines()[-1])[:200]
        return bucket, False, diag_line

    if clean_disk_write or aider_ok or any(m in low for m in _LOOP_SUCCESS_MARKERS):
        return "OK", True, ""

    if is_write:
        return "WRITE_OTHER", False, ""
    return "READ_INFO", False, ""


def build_iteration_stagnation_signature(tool_results: List[Dict[str, Any]]) -> Tuple[str, bool, bool, str]:
    """
    Build a deterministic signature for an agent iteration's tool calls & outcomes.
    Returns (signature, had_any_progress, all_nonwrite_failures, diagnostic_summary).
    """
    parts: List[str] = []
    any_progress = False
    any_write_call = False
    any_failure = False
    last_diag = ""

    for res in tool_results or []:
        tag = str(res.get("tag") or "").upper()
        action = str(res.get("action") or "")
        args_sig = _DYNAMIC_TRACE_NOISE_RE.sub("", str(res.get("args_sig") or ""))
        bucket, prog, diag = classify_tool_result_for_loop(res)
        parts.append(f"{tag}:{action}:{args_sig}:{bucket}")
        if prog:
            any_progress = True
        if action in {"write_file", "patch_file", "run_aider_task"}:
            any_write_call = True
        if bucket.startswith("FAIL:"):
            any_failure = True
            if diag:
                last_diag = diag

    return "||".join(parts), any_progress, (any_failure and not any_write_call), last_diag


class LoopStagnationTracker:
    """Tracks consecutive repetitive or failing iterations and emits nudge/break actions."""

    def __init__(self) -> None:
        self.last_sig: str = ""
        self.repeat_streak: int = 0
        self.unfixed_fail_streak: int = 0
        self.last_diag: str = ""

    def step(self, tool_results: List[Dict[str, Any]]) -> Tuple[str, str, str]:
        """
        Inspect current iteration tool results.
        Returns (decision: 'continue' | 'nudge' | 'break', user_message_or_notice, diag_summary).
        """
        sig, any_progress, nonwrite_fail, diag = build_iteration_stagnation_signature(tool_results)
        if diag:
            self.last_diag = diag

        if sig and sig == self.last_sig and not any_progress:
            self.repeat_streak += 1
        else:
            self.last_sig = sig
            self.repeat_streak = 1 if (sig and not any_progress) else 0

        if nonwrite_fail:
            self.unfixed_fail_streak += 1
        elif any_progress:
            self.unfixed_fail_streak = 0

        tools_brief = ", ".join(
            sorted({str(r.get("action") or r.get("tag") or "tool") for r in (tool_results or [])})
        )
        diag_hint = f" Last error: {self.last_diag}" if self.last_diag else ""

        if self.repeat_streak >= 3 or self.unfixed_fail_streak >= 5:
            notice = (
                f"> ⚠️ **Loop Breaker:** Stopped after {max(self.repeat_streak, self.unfixed_fail_streak)} "
                f"repetitive failing step(s) (`{tools_brief}`) with no file fixes.{diag_hint}"
            )
            return "break", notice, self.last_diag

        if self.repeat_streak == 2 or self.unfixed_fail_streak == 3:
            nudge = (
                f"[SYSTEM LOOP BREAKER]: You repeated the same failing call(s) ({tools_brief}) "
                f"without fixing the underlying code.{diag_hint}\n"
                "STOP re-running start_app / probe_url / test_app / get_app_logs unchanged!\n"
                "Do one of these concrete actions NEXT:\n"
                "1. Call EXECUTOR__read_file on the broken source file (e.g. app.py / test_app.py / index.html) to inspect the real code.\n"
                "2. Fix it cleanly with EXECUTOR__patch_file / EXECUTOR__write_file, OR delegate the fix cleanly to EXECUTOR__run_aider_task."
            )
            return "nudge", nudge, self.last_diag

        return "continue", "", self.last_diag
