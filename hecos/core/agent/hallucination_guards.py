"""
hecos/core/agent/hallucination_guards.py
Intent checks and anti-hallucination guards for missing image_gen, NetSearch, Streaming, and Executor file edits.
"""

from __future__ import annotations

import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

from hecos.core.logging import logger
from hecos.core.agent.traces import AgentTracer
from hecos.core.agent.trace_labeler import tr

# --- IMAGE GEN MISSING-PLUGIN GUARDS ---

_IMAGE_GEN_INTENT_RE = re.compile(
    r'(\b(?:genera|generami|generare|crea|creami|creare|disegna|disegnami|disegnare|'
    r'fai|fammi|fare|scatta|scattami|scattare|mandami|manda|inviami|invia|mostrami|mostra|'
    r'voglio\s+vedere|fammi\s+vedere|generate|create|draw|make|send\s+me|show\s+me|take)\b'
    r'[^\r\n]{0,45}\b(?:una?\s+tua\s+foto|una?\s+foto|foto\s+tua|selfie|immagine|immagini|'
    r'ritratto|illustrazione|disegno|photo|picture|image|portrait)\b'
    r'|\b(?:foto\s+tua|tuo\s+selfie|un\s+selfie)\b)',
    re.IGNORECASE,
)

_WEB_SEARCH_EXCLUSION_RE = re.compile(
    r'\b(?:cerca|cercami|cercare|trova|trovami|trovare|search|find|google|duckduckgo|searxng|'
    r'sul\s+web|in\s+rete|su\s+internet|online|webcam)\b',
    re.IGNORECASE,
)


def is_uninstalled_image_gen_request(user_text: str) -> bool:
    """Return True when the user asks for AI image/photo generation while `image_gen` plugin is inactive."""
    if not user_text or not isinstance(user_text, str):
        return False
    clean = user_text.strip()
    if clean.startswith("/"):
        return False
    if _WEB_SEARCH_EXCLUSION_RE.search(clean):
        return False
    if not _IMAGE_GEN_INTENT_RE.search(clean):
        return False
    try:
        from hecos.core.llm.prompt_builder import _is_image_gen_plugin_active
        return not _is_image_gen_plugin_active()
    except Exception:
        return False


def emit_missing_image_gen_warning() -> None:
    """Emit trace steps and UI action box informing that `image_gen` is not installed."""
    logger.warning("[AGENT] User requested image/photo generation, but 'image_gen' plugin is not installed.")
    err_step = AgentTracer.start_step(
        kind="error",
        label=tr("Pacchetto 'image_gen' non installato", "Package 'image_gen' is not installed"),
        icon="fa-triangle-exclamation",
        level="error",
        module_name=tr("Generazione Immagine", "Image Generation"),
    )
    AgentTracer.finish_step(
        err_step,
        status="error",
        result_preview=tr("Disponibile nello Store / HPM", "Available in Store / HPM"),
    )
    try:
        AgentTracer.emit_action(
            "IMAGE_GEN",
            "missing_plugin",
            "Plugin 'image_gen' is not installed (available in Store / HPM)",
        )
    except Exception:
        pass


# --- NETSEARCH ANTI-HALLUCINATION GUARDS ---

_NETSEARCH_REQUEST_RE = re.compile(
    r'(?:'
    r'\b(?:cerca|cercami|cercare|trova|trovami|trovare|ricerca|recupera|scova|scarica|'
    r'search|find|look\s+up|fetch|scrape|browse)\b'
    r'.{0,60}\b(?:su\s+internet|in\s+rete|sul\s+web|online|web|video|filmat[io]|clip|'
    r'foto\s+e\s+video|immagini\s+e\s+video|foto\s+di|immagini\s+di|materiale|fonti|'
    r'notizie|articoli|documenti|pdf|torrent|archivi|siti?|link|onion|dark\s*web|osint|avvistament[io])\b'
    r'|\b(?:foto\s+e\s+video|immagini\s+e\s+video|video\s+e\s+foto|avvistament[io]|'
    r'cerca\s+sul\s+web|cerca\s+online|cerca\s+in\s+rete|trova\s+online)\b'
    r')',
    re.IGNORECASE | re.DOTALL,
)


def are_netsearch_tools_enabled(cfg: Optional[dict]) -> bool:
    """Return True if Net Search tools or direct search commands are enabled in config."""
    if not isinstance(cfg, dict):
        return True
    if cfg.get("disable_tools", False):
        return False
    plugins_cfg = cfg.get("plugins") or {}
    if plugins_cfg.get("NETSEARCH", {}).get("enabled", True) is False:
        return False
    try:
        from hecos.modules.net_search.search.config import is_netsearch_package_enabled
        if not is_netsearch_package_enabled():
            return False
    except Exception:
        pass
    pctrl = cfg.get("payload_control") or {}
    if not pctrl.get("send_tools", True):
        return True
    mode = str(pctrl.get("tool_selection_mode") or "all").strip().lower()
    if mode != "custom":
        return True
    selected = {str(x).strip() for x in (pctrl.get("selected_tools") or [])}
    return any(s.startswith("NETSEARCH__") or s == "NETSEARCH" for s in selected)


def detect_unexecuted_netsearch_request(user_text: Optional[str], assistant_text: Optional[str]) -> bool:
    """Return True when user asked to search online/media and assistant replied without searching."""
    if not user_text or not isinstance(user_text, str):
        return False
    clean_u = user_text.strip()
    if not clean_u or clean_u.startswith("/"):
        return False
    if not _NETSEARCH_REQUEST_RE.search(clean_u):
        return False
    ans = (assistant_text or "").strip()
    if len(ans) < 20:
        return False
    if "[[HSEARCH:" in ans or "[[HMEDIA:" in ans:
        return False
    return True


def get_netsearch_unexecuted_guard_message() -> Optional[str]:
    """Read the configurable Net Search anti-hallucination guard prompt (None if disabled)."""
    try:
        from hecos.modules.net_search.search.config import get_ai_prompts_config
        ai_cfg = get_ai_prompts_config()
        if not ai_cfg.get("enable_unexecuted_guard", True):
            return None
        msg = str(ai_cfg.get("unexecuted_guard_prompt") or "").strip()
        return msg or None
    except Exception:
        return None


# --- EXECUTOR FILE VERIFICATION & ANTI-HALLUCINATION GUARDS ---

_FILE_CLAIM_RE = re.compile(
    r'(?:\b(?:i(?:\s+have|\'ve)?\s+(?:already\s+)?(?:created|written|generated|saved|patched|updated|fixed|resolved|started|launched|verified)'
    r'|files?\s+(?:created|written|generated|saved|updated)'
    r'|ho\s+(?:gi[aà]\s+|preso\s+[^\n]{0,60}\be\s+ho\s+)?(?:creato|scritto|generato|salvato|sistemato|corretto|risolto|modificato|aggiornato|riparato|avviato|verificato|eseguito|applicato|patchato|iniziato\s+a\s+creare)'
    r'|file\s+(?:creati|scritti|salvati|aggiornati)'
    r'|progetto\s+[eè]\s+ora\s+(?:attivo|sincronizzato|pronto))\b'
    r'|`?[A-Za-z0-9_./\\-]+\.(?:py|js|ts|jsx|tsx|json|ya?ml|html?|css|sh|bat|md|txt)`?'
    r'(?:.{0,80}\b(?:created|written|saved|updated|fixed|started|creato|creati|salvato|aggiornato|aggiornati|corretto|pronto\s+per|ready)\b))',
    re.IGNORECASE | re.DOTALL,
)

_NEGATIVE_FILE_CLAIM_RE = re.compile(
    r'\b(?:haven\'t|have\s+not|did\s+not|didn\'t|no\s+files?\s+(?:were\s+)?(?:created|written|saved)'
    r'|non\s+ho\s+(?:ancora\s+)?(?:creato|scritto|salvato)|nessun\s+file)\b',
    re.IGNORECASE,
)

_WRITE_EXECUTOR_ACTIONS = frozenset({
    "write_file", "patch_file", "run_aider_task", "git_restore", "move_path", "create_dir", "delete_file",
})


def extract_verified_files_from_results(accumulated_tool_results: List[Dict[str, Any]]) -> List[Tuple[str, str, str]]:
    """
    Scan EXECUTOR tool results and return a deduplicated list of verified files
    that genuinely exist on disk: [(abs_path, file_uri, basename), ...].
    """
    verified: List[Tuple[str, str, str]] = []
    seen_lower = set()
    uri_re = re.compile(r'\|\s*URI:\s*(file:///[^\r\n]+)', re.IGNORECASE)
    legacy_re = re.compile(r'\[EXECUTOR\]\s+File\s+(?:written|patched)[^:]*:\s*([^\r\n(]+)', re.IGNORECASE)

    for res in accumulated_tool_results or []:
        tag = str(res.get("tag", "")).upper()
        if tag != "EXECUTOR":
            continue
        out = str(res.get("output", "") or "")
        candidates: List[str] = []
        for m in uri_re.finditer(out):
            uri_val = m.group(1).strip()
            raw_path = uri_val[8:] if uri_val.lower().startswith("file:///") else uri_val
            candidates.append(raw_path.replace("/", os.sep))
        if not candidates:
            for m in legacy_re.finditer(out):
                candidates.append(m.group(1).strip())

        for cand in candidates:
            abs_p = os.path.abspath(cand)
            key = abs_p.lower()
            if key in seen_lower:
                continue
            if os.path.isfile(abs_p):
                seen_lower.add(key)
                file_uri = "file:///" + abs_p.replace("\\", "/")
                verified.append((abs_p, file_uri, os.path.basename(abs_p)))
    return verified


def are_executor_write_tools_enabled(cfg: Optional[dict]) -> bool:
    """Return True if EXECUTOR file-writing tools are currently exposed in config/payload_control."""
    if not isinstance(cfg, dict):
        return True
    if cfg.get("disable_tools", False):
        return False
    pctrl = cfg.get("payload_control") or {}
    if not pctrl.get("send_tools", True):
        return False
    plugins_cfg = cfg.get("plugins") or {}
    if not plugins_cfg.get("EXECUTOR", {}).get("enabled", True):
        return False
    if not plugins_cfg.get("EXECUTOR", {}).get("llm_callable", True):
        return False
    mode = str(pctrl.get("tool_selection_mode") or "all").strip().lower()
    if mode != "custom":
        return True
    selected = {str(x).strip() for x in (pctrl.get("selected_tools") or [])}
    return bool(selected & {"EXECUTOR__*", "EXECUTOR__write_file", "EXECUTOR__patch_file", "EXECUTOR__run_aider_task"})


def is_executor_anti_hallucination_enabled(cfg: Optional[dict]) -> bool:
    """Return True if Executor anti-hallucination guard & retry is enabled (default True)."""
    if isinstance(cfg, dict):
        ex_cfg = (cfg.get("plugins") or {}).get("EXECUTOR")
        if isinstance(ex_cfg, dict) and "enable_anti_hallucination_guard" in ex_cfg:
            return bool(ex_cfg["enable_anti_hallucination_guard"])
    try:
        cfg_mgr = getattr(sys, "hecos_config_manager", None)
        if cfg_mgr:
            return bool(cfg_mgr.get_plugin_config("EXECUTOR", "enable_anti_hallucination_guard", True))
    except Exception:
        pass
    return True


def _has_nonexistent_file_uri(text: str) -> bool:
    """Return True if text embeds a local file:/// link pointing to a path missing on disk."""
    for raw_uri in re.findall(r'file:///([^\s)\]\'"<>`]+)', text, re.IGNORECASE):
        norm = raw_uri.strip().rstrip(".,;:")
        lower = norm.lower()
        if not norm or "path/to/" in lower or "..." in lower:
            continue
        candidate = norm.replace("/", os.sep)
        if not os.path.exists(candidate):
            return True
    return False


def detect_unexecuted_file_claim(text: Optional[str]) -> bool:
    """Detect when plain assistant text claims files were created or emits dead file:/// links without tool execution."""
    if not text or not isinstance(text, str):
        return False
    if _has_nonexistent_file_uri(text):
        return True
    if _NEGATIVE_FILE_CLAIM_RE.search(text):
        return False
    if not _FILE_CLAIM_RE.search(text):
        return False
    return bool(re.search(
        r'(?:[A-Za-z0-9_.-]+\.(?:py|js|ts|jsx|tsx|json|ya?ml|html?|css|sh|bat|md|txt)\b|\b(?:cli|core|utils|src|tests)/)',
        text,
        re.IGNORECASE,
    ))


def append_verified_file_links(text: str, verified_files: List[Tuple[str, str, str]]) -> str:
    """Append real Markdown file links for disk-verified files missing from the response."""
    if not verified_files:
        return text
    existing_lower = text.lower()
    missing_links: List[str] = []
    for abs_p, file_uri, fname in verified_files:
        uri_slash = abs_p.replace("\\", "/").lower()
        if file_uri.lower() in existing_lower or uri_slash in existing_lower:
            continue
        missing_links.append(f"- [📄 {fname}]({file_uri})")
    if not missing_links:
        return text
    section = "### Verified Files Created on Disk\n" + "\n".join(missing_links)
    return f"{text.rstrip()}\n\n{section}".strip()


_LLM_ERROR_PREFIXES = ("⚠️", "❌", "⛔", "🔌", "🔑", "🚫", "[SYSTEM")


def is_llm_error_response(text: Optional[str]) -> bool:
    """Return True if text is a system/LLM error notice rather than a real model completion."""
    stripped = str(text or "").lstrip()
    return bool(stripped and stripped.startswith(_LLM_ERROR_PREFIXES))


def evaluate_plain_text_guards(
    *,
    user_text: str,
    raw_response: Any,
    extracted_text: Optional[str],
    accumulated_tool_results: List[Dict[str, Any]],
    current_cfg: Optional[dict],
    iteration: int,
    max_iterations: int,
    retries_state: Dict[str, int],
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Evaluate streaming, Executor, and NetSearch anti-hallucination guards when a turn produced plain text.
    Mutates `retries_state` counters in place.
    Returns `(guard_prompt_to_retry, step_trace_preview, unverified_file_notice)`.
    """
    if is_llm_error_response(extracted_text):
        return None, None, None

    fake_stream_claim = any(
        tok in (extracted_text or "")
        for tok in ("📺 Tuned to", "Launched in VLC Desktop", "⏹️ Live Stream stopped")
    )
    stream_tool_already_ran = any(
        r.get("action") in ("stream_control", "stream_search")
        or "📺 Tuned to" in str(r.get("output", ""))
        or "Live Stream stopped" in str(r.get("output", ""))
        for r in accumulated_tool_results
    )
    if (
        fake_stream_claim
        and not stream_tool_already_ran
        and retries_state.get("stream", 0) < 1
        and iteration < max_iterations
    ):
        retries_state["stream"] = retries_state.get("stream", 0) + 1
        logger.warning("[AGENT] Caught unexecuted stream status badge hallucination — forcing tool retry.")
        return (
            "[SYSTEM GUARD]: You wrote a fake '📺 Tuned to...' text line without actually calling any tool, "
            "so VLC/player was NOT changed. Emit `NETSEARCH__stream_control(action='play', query='<requested channel>', category='tv')` "
            "(or `/canale <channel>` on its own line) NOW to execute it for real.",
            tr("Rilevato falso stato streaming — richiamo il tool", "Detected unexecuted stream badge — retrying tool call"),
            None,
        )

    verified_disk_files = extract_verified_files_from_results(accumulated_tool_results)
    executor_mutated_disk = bool(verified_disk_files) or any(
        str(r.get("tag", "")).upper() == "EXECUTOR"
        and str(r.get("action") or "") in _WRITE_EXECUTOR_ACTIONS
        and "SYNTAX ERROR" not in str(r.get("output", ""))
        and "Path not found:" not in str(r.get("output", ""))
        and "Text to replace not found" not in str(r.get("output", ""))
        for r in accumulated_tool_results
    )
    echoed_tool_resp = "<tool_response>" in str(raw_response or "").lower()
    parroted_loop_breaker = (
        "Loop Breaker: Stopped after" in (extracted_text or "")
        or ("> ⚠️" in (extracted_text or "") and "SYNTAX ERROR" in (extracted_text or ""))
    )

    unverified_file_notice: Optional[str] = None
    is_plan_only_turn = bool(
        isinstance(current_cfg, dict)
        and (
            current_cfg.get("_turn_plan_only")
            or (
                not current_cfg.get("_turn_execute_plan")
                and not current_cfg.get("_turn_fast_code")
                and str((current_cfg.get("plugins") or {}).get("ACTION_PLANS", {}).get("plan_mode") or "").lower() == "plan_only"
            )
        )
    )
    if (
        not is_plan_only_turn
        and (
            (not executor_mutated_disk and not verified_disk_files and detect_unexecuted_file_claim(extracted_text))
            or (echoed_tool_resp and not verified_disk_files)
            or parroted_loop_breaker
        )
        and is_executor_anti_hallucination_enabled(current_cfg)
    ):
        if are_executor_write_tools_enabled(current_cfg):
            if retries_state.get("file", 0) < 2 and iteration < max_iterations:
                retries_state["file"] = retries_state.get("file", 0) + 1
                logger.warning(
                    "[AGENT] Caught unexecuted EXECUTOR claim / <tool_response> / Loop Breaker parrot — forcing real EXECUTOR tool retry."
                )
                if echoed_tool_resp:
                    guard_content = (
                        "[SYSTEM GUARD]: Do NOT echo `<tool_response>` text! Output real tool calls only. "
                        "Invoke `EXECUTOR__run_aider_task` or write ONE concise file per turn via `EXECUTOR__write_file` "
                        "(with forward slashes `/` in Windows paths) right now."
                    )
                elif parroted_loop_breaker:
                    guard_content = (
                        "[SYSTEM GUARD]: You repeated an old Loop Breaker error from chat history instead of fixing the files! "
                        "Call `EXECUTOR__read_file` on the target files (e.g. `storage.py`, `app.py`, `static/app.js`, `index.html`) "
                        "and apply real fixes with `EXECUTOR__write_file` / `EXECUTOR__patch_file` now."
                    )
                else:
                    guard_content = (
                        "[SYSTEM GUARD]: You claimed files were created, patched, or fixed, "
                        "but NO file write/patch succeeded on disk yet (`_verified_disk_files` is empty). "
                        "Call `EXECUTOR__read_file` to inspect the actual file lines, then fix it cleanly with `EXECUTOR__write_file` "
                        "or `EXECUTOR__patch_file` (using forward slashes `/` in Windows paths)."
                    )
                return (
                    guard_content,
                    tr("Rilevata risposta simulata — richiamo EXECUTOR", "Detected unexecuted claim or echoed error — retrying EXECUTOR"),
                    None,
                )
            unverified_file_notice = (
                "> ⚠️ **System Notice:** No files were actually written or modified on disk in this turn "
                "(no `EXECUTOR` tool was invoked)."
            )
        else:
            unverified_file_notice = (
                "> ⚠️ **System Notice:** No files were written to disk because filesystem write tools "
                "(`EXECUTOR__write_file` / `patch_file`) are disabled in Payload & Tools Control."
            )

    netsearch_already_ran = any(
        str(r.get("tag", "")).upper() in ("NETSEARCH", "SLASH_COMMAND")
        or "[[HSEARCH:" in str(r.get("output", ""))
        or "[[HMEDIA:" in str(r.get("output", ""))
        for r in accumulated_tool_results
    )
    if (
        not netsearch_already_ran
        and retries_state.get("netsearch", 0) < 1
        and iteration < max_iterations
        and are_netsearch_tools_enabled(current_cfg)
        and detect_unexecuted_netsearch_request(user_text, extracted_text)
    ):
        guard_msg = get_netsearch_unexecuted_guard_message()
        if guard_msg:
            retries_state["netsearch"] = retries_state.get("netsearch", 0) + 1
            logger.warning("[AGENT] Caught unexecuted Net Search request — forcing real search tool retry.")
            return (
                guard_msg,
                tr("Ricerca non eseguita — richiamo Net Search", "Search skipped — retrying with Net Search"),
                None,
            )

    return None, None, unverified_file_notice
