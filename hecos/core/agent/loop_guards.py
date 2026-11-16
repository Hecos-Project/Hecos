"""
hecos/core/agent/loop_guards.py
Modular guards, intent detectors, early-termination heuristics,
and lifecycle helpers for the Hecos Agentic Loop.
"""

import json
import os
import re
import threading
from typing import Any, Dict, List, Optional, Tuple

from hecos.core.logging import logger
from hecos.core.agent.traces import AgentTracer
from hecos.core.agent.trace_labeler import tr
from hecos.core.agent.media_interceptor import MediaInterceptor
from hecos.core.processing import processore
from hecos.core.i18n import translator


# --- 1. INTENT REGEX & MISSING PLUGIN GUARDS ---

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

_DOC_INTENT_RE = re.compile(
    r'\b(?:documento|documenti|doc|pdf|html|scheda|file)\b',
    re.IGNORECASE,
)


def is_uninstalled_image_gen_request(user_text: str) -> bool:
    """
    Returns True when the user's message asks for AI image/photo generation,
    is NOT a web search or webcam request, and the `image_gen` plugin is NOT active.
    """
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
    """Emits trace steps and UI action box informing that `image_gen` is not installed."""
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


def resolve_short_model_label(cfg: dict) -> str:
    """Extracts a clean short model name from the active config for trace display."""
    try:
        try:
            from app.model_manager import ModelManager
        except ImportError:
            from hecos.app.model_manager import ModelManager
        btype, mname = ModelManager.get_effective_model_info(cfg)
        if mname:
            short = str(mname).split("/")[-1]
            return f"{short} ({btype})" if btype else short
    except Exception:
        pass
    return ""


# --- 2. BACKGROUND WATCHDOG KEEPALIVE ---

class LoopWatchdog:
    """
    Context manager that keeps the SSE/inference watchdog alive via silent
    heartbeat events without polluting the trace UI or console.
    """

    def __init__(self, trace_callback, interval_seconds: float = 15.0):
        self.trace_callback = trace_callback
        self.interval_seconds = interval_seconds
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def __enter__(self):
        if not self.trace_callback:
            return self

        def _keepalive():
            while not self._stop_event.wait(self.interval_seconds):
                if self.trace_callback:
                    try:
                        self.trace_callback({"type": "heartbeat"}, "info")
                    except Exception:
                        pass

        self._thread = threading.Thread(target=_keepalive, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._thread:
            self._stop_event.set()
            self._thread.join(0.2)


# --- 3. MULTIMODAL PERCEPTION HELPER ---

def process_initial_vision(
    user_text: str,
    images: Optional[List[Any]],
    current_cfg: dict,
    emit_callback=None,
) -> Tuple[str, Optional[List[Any]]]:
    """Runs VisionRouter on turn 1 if images are present and records the trace step."""
    if not images:
        return user_text, images

    try:
        from hecos.modules.web_ui.vision import VisionRouter
        try:
            from app.model_manager import ModelManager
        except ImportError:
            from hecos.app.model_manager import ModelManager

        _btype, _mname = ModelManager.get_effective_model_info(current_cfg)
        v_step = AgentTracer.start_step(
            kind="vision",
            label=tr("Analisi visiva immagini allegate", "Visual analysis of attached images"),
            args_preview=tr(f"{len(images)} immagine/i", f"{len(images)} image(s)"),
            icon="fa-eye",
            level="info",
            module_name="Vision AI",
        )
        user_text, images = VisionRouter.process_incoming_turn(
            user_text, images, _mname, _btype, emit_callback=emit_callback
        )
        AgentTracer.finish_step(v_step, status="ok")
    except Exception as _v_err:
        logger.debug(f"[AGENT] Vision routing exception: {_v_err}")

    return user_text, images


# --- 4. EARLY TERMINATION / SHORT-CIRCUITING HEURISTICS ---

def eval_early_termination(
    user_text: str,
    accumulated_tool_results: List[Dict[str, Any]],
    extracted_text: Optional[str],
    state_manager: Any,
    images: Optional[List[Any]],
    iteration: int,
) -> Tuple[bool, str]:
    """
    Evaluates whether the agent has already fulfilled the user's intent
    (e.g., image generated, web search cards produced, document created)
    and can conclude the turn early without wasteful extra iterations.

    Returns:
        (should_terminate: bool, reason_message: str)
    """
    cleaned_for_len = str(extracted_text or "")
    try:
        from hecos.core.processing.parsers.legacy_tag_parser import strip_module_call_syntax
        cleaned_for_len = strip_module_call_syntax(cleaned_for_len)
    except Exception:
        pass
    has_text = bool(cleaned_for_len and len(cleaned_for_len.strip()) > 10)
    has_generated_img = any("[[IMG:" in str(r.get("output", "")) for r in accumulated_tool_results)

    image_limit = getattr(state_manager, "requested_image_limit", 1) if state_manager else 1
    images_done = getattr(state_manager, "total_images_in_turn", 0) if state_manager else 0
    all_images_done = (images_done >= image_limit) if image_limit > 0 else True

    wants_doc = bool(_DOC_INTENT_RE.search(user_text or ""))
    has_doc = any(
        r.get("tag") in ("DOCS", "DOCUMENT_MAKER", "DOCUMENT_READER")
        or "PDF:" in str(r.get("output", ""))
        or "HTML:" in str(r.get("output", ""))
        for r in accumulated_tool_results
    )
    doc_satisfied = (not wants_doc) or has_doc

    def _is_err(out_str: str) -> bool:
        s = out_str.lstrip()
        return s.startswith(("Error:", "⚠️", "[SYSTEM ERROR"))

    has_search_card = any(
        (not _is_err(str(r.get("output", ""))))
        and (
            "[[HSEARCH:" in str(r.get("output", ""))
            or "[[HMEDIA:" in str(r.get("output", ""))
            or str(r.get("output", "")).lstrip().startswith((
                "📺 Tuned to",
                "⏹️ Live Stream stopped",
            ))
        )
        for r in accumulated_tool_results
    )

    has_pending_vision_review = bool(images and len(images) > 0 and iteration == 1 and has_search_card)
    wants_synthesis = bool(_NETSEARCH_SYNTHESIS_INTENT_RE.search(user_text or ""))

    if has_generated_img and all_images_done and doc_satisfied:
        # Terminate as soon as all requested images are done, regardless of whether the
        # model emitted any text in this step (text will be synthesised in finalize_response).
        return True, tr(
            "Immagine generata e risposta formulata",
            "Image generated and response formulated",
        )

    if has_search_card and not has_pending_vision_review and doc_satisfied and has_text:
        if iteration == 1 and wants_synthesis:
            return False, ""
        return True, tr(
            "Ricerca completata e risposta formulata",
            "Search completed and response formulated",
        )

    return False, ""


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

_NETSEARCH_SYNTHESIS_INTENT_RE = re.compile(
    r'\b(?:sunto|riassunt[io]|riassumi|sintesi|sintetizza|spiega|spiegami|analizza|'
    r'confronta|commenta|descrivi|summariz\w*|summary|analy[sz]\w*|explain|digest|synthesi[sz]\w*)\b',
    re.IGNORECASE,
)


def are_netsearch_tools_enabled(cfg: Optional[dict]) -> bool:
    """Returns True if Net Search tools or direct search commands are enabled in config."""
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
    """Returns True when user asked to search online/media and assistant replied in plain text without searching."""
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
    """Reads the configurable Net Search anti-hallucination guard prompt (None if disabled)."""
    try:
        from hecos.modules.net_search.search.config import get_ai_prompts_config
        ai_cfg = get_ai_prompts_config()
        if not ai_cfg.get("enable_unexecuted_guard", True):
            return None
        msg = str(ai_cfg.get("unexecuted_guard_prompt") or "").strip()
        return msg or None
    except Exception:
        return None


# --- 5. RESPONSE FINALIZATION & SAFETY FORMATTER ---

# --- 5. FILE CREATION TRACKING, ANTI-HALLUCINATION GUARD & STANDARDIZED FINAL RESPONSE ---

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


def extract_verified_files_from_results(accumulated_tool_results: List[Dict[str, Any]]) -> List[Tuple[str, str, str]]:
    """
    Scans EXECUTOR tool results and returns a deduplicated list of verified files
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
    """Returns True if EXECUTOR file-writing tools are currently exposed in config/payload_control."""
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
    """Returns True if Executor anti-hallucination guard & retry is enabled (default True)."""
    if isinstance(cfg, dict):
        ex_cfg = (cfg.get("plugins") or {}).get("EXECUTOR")
        if isinstance(ex_cfg, dict) and "enable_anti_hallucination_guard" in ex_cfg:
            return bool(ex_cfg["enable_anti_hallucination_guard"])
    try:
        import sys
        cfg_mgr = getattr(sys, "hecos_config_manager", None)
        if cfg_mgr:
            return bool(cfg_mgr.get_plugin_config("EXECUTOR", "enable_anti_hallucination_guard", True))
    except Exception:
        pass
    return True


def _has_nonexistent_file_uri(text: str) -> bool:
    """Returns True if text embeds a local file:/// link pointing to a path missing on disk."""
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
    """Detects when plain assistant text claims files were created or emits dead file:/// links without tool execution."""
    if not text or not isinstance(text, str):
        return False
    if _has_nonexistent_file_uri(text):
        return True
    if _NEGATIVE_FILE_CLAIM_RE.search(text):
        return False
    has_claim = bool(_FILE_CLAIM_RE.search(text))
    if not has_claim:
        return False
    # Require concrete file/folder evidence (e.g. main.py, cli/, utils/, file path) to avoid conversational false positives
    has_artifact_ref = bool(re.search(
        r'(?:[A-Za-z0-9_.-]+\.(?:py|js|ts|jsx|tsx|json|ya?ml|html?|css|sh|bat|md|txt)\b|\b(?:cli|core|utils|src|tests)/)',
        text,
        re.IGNORECASE,
    ))
    return has_artifact_ref


def append_verified_file_links(text: str, verified_files: List[Tuple[str, str, str]]) -> str:
    """Appends real Markdown file links for disk-verified files missing from the response."""
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


def finalize_response(
    extracted_text: Optional[str],
    accumulated_tool_results: List[Dict[str, Any]],
    raw_response: Any,
    voice_status: bool,
    think_block: Optional[str] = None,
    missing_igen_detected: bool = False,
    unverified_file_notice: Optional[str] = None,
) -> Tuple[str, str]:
    """
    Standardizes the final response formatting across all termination paths:
    1. Handles empty text fallback
    2. Applies content filter safety message
    3. Wraps think block
    4. Injects missing plugin system notices
    5. Appends rich media tokens via MediaInterceptor
    6. Cleans final speech and video text via processore
    """
    text = extracted_text or ""

    if not text.strip():
        if accumulated_tool_results:
            tags = ", ".join([str(r.get("tag", "")) for r in accumulated_tool_results if r.get("tag")])
            text = f"I have executed the requested actions: {tags}."
        elif think_block:
            text = "I've analyzed your request but couldn't formulate a final response. Please try rephrasing or using a different model."
        else:
            text = "I'm thinking, but I don't have a specific text response yet. How can I help further?"

    if "!!!BLOCK_SAFETY!!!" in str(text):
        if translator.get_translator().language == "it":
            text = "Spiacente, questa richiesta è stata bloccata dai filtri di sicurezza del provider AI (Content Filter). Prova a riformulare con termini meno sensibili."
        else:
            text = "I'm sorry, but this request was blocked by the AI provider's safety filters (Content Filter). Please try rephrasing with less sensitive terms."

    if think_block and "<think>" not in text.lower():
        text = f"<think>\n{think_block}\n</think>\n\n{text}"

    # If `image_gen` is missing and user asked for photo/image, attach clear system alert
    if missing_igen_detected and not any("[[IGEN_ALERT]]" in str(r.get("output", "")) for r in accumulated_tool_results):
        accumulated_tool_results.append({
            "id": "sys_missing_igen",
            "tag": "SYSTEM",
            "output": (
                "[[IGEN_ALERT]]\n"
                "💡 **System Notice — Missing Plugin (`image_gen`)**\n"
                "The **Image Generation (`image_gen`)** package is not currently installed or active. "
                "To enable photo and image generation, install it from the **Packages / Store (HPM)** section.\n"
                "[[/IGEN_ALERT]]"
            ),
        })

    # Append real clickable links for all verified disk files created/patched by EXECUTOR
    verified_files = extract_verified_files_from_results(accumulated_tool_results)
    if verified_files:
        text = append_verified_file_links(text, verified_files)
    elif unverified_file_notice:
        text = f"{text.rstrip()}\n\n{unverified_file_notice}".strip()

    # Append UI images and rich media tokens
    text = MediaInterceptor.append_ui_media_to_text(text, accumulated_tool_results)

    video_response, clean_voice = processore.clean_final_output(
        text, accumulated_tool_results, raw_response, voice_status
    )
    return video_response, clean_voice


# --- 6. ASSISTANT HISTORY PERSISTENCE ---

def sync_assistant_history(
    config: Any,
    current_user_id: str,
    session_id: Optional[str],
    sender_tab_id: Optional[str],
    agent_config: dict,
    last_trace_summary: Optional[dict],
    video_response: str,
    think_block: Optional[str] = None,
    user_text: Optional[str] = None,
) -> None:
    """Ensures final response and trace summary are persisted into SQLite history."""
    try:
        from hecos.memory import brain_interface
        from hecos.core.llm.client import LAST_PAYLOAD_INFO
        from hecos.core.llm.history_manager import HistoryManager

        if user_text and not HistoryManager._has_trailing_matching_user_msg(
            user_text, user_id=current_user_id, session_id=session_id
        ):
            brain_interface.save_message(
                "user",
                user_text,
                config=config,
                user_id=current_user_id,
                session_id=session_id,
                sender_tab_id=sender_tab_id,
            )

        hist_text = video_response or ""
        if think_block and "<think>" not in hist_text.lower():
            hist_text = f"<think>\n{think_block}\n</think>\n\n{hist_text}"

        ai_cfg = (config or {}).get("ai", {}) if isinstance(config, dict) else {}
        raw_persona = ai_cfg.get("active_personality") or "Hecos_System_Soul"
        clean_persona = raw_persona.replace(".yaml", "") if isinstance(raw_persona, str) else "Hecos_System_Soul"

        model_info = LAST_PAYLOAD_INFO.get("model_info")

        if last_trace_summary and agent_config.get("trace_persist_history", True):
            try:
                m_dict = json.loads(model_info) if model_info else {}
                m_dict["agent_trace"] = last_trace_summary
                model_info = json.dumps(m_dict)
            except Exception:
                pass

        brain_interface.upsert_last_assistant_message(
            hist_text,
            config=config,
            user_id=current_user_id,
            session_id=session_id,
            persona_name=clean_persona,
            sender_tab_id=sender_tab_id,
            model_info=model_info,
        )
    except Exception as e:
        logger.debug(f"[AGENT] Failed to sync assistant history: {e}")


# --- 7. REPETITIVE / STAGNANT LOOP BREAKER ---

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
        # Extract concise failure diagnostic line (syntax/web/test/http error)
        diag_line = ""
        for ln in out.splitlines():
            s = ln.strip()
            if any(k in s.lower() for k in ("web-diagnostic", "syntax error", "importerror", "modulenotfounderror", "health-check failed", "path not found", "unknown run_id", "timed out")):
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

