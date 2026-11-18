"""
hecos/core/agent/response_finalizer.py
Agent loop watchdog, vision turn router, early-termination evaluator,
final response formatter, and unified DB history synchronization.
"""

from __future__ import annotations

import re
import threading
from typing import Any, Dict, List, Optional, Tuple

from hecos.core.logging import logger
from hecos.core.agent.traces import AgentTracer
from hecos.core.agent.trace_labeler import tr
from hecos.core.agent.media_interceptor import MediaInterceptor
from hecos.core.agent.hallucination_guards import (
    append_verified_file_links,
    extract_verified_files_from_results,
)
from hecos.core.processing import processore
from hecos.core.i18n import translator

_DOC_INTENT_RE = re.compile(
    r'\b(?:documento|documenti|doc|pdf|html|scheda|file)\b',
    re.IGNORECASE,
)

_NETSEARCH_SYNTHESIS_INTENT_RE = re.compile(
    r'\b(?:sunto|riassunt[io]|riassumi|sintesi|sintetizza|spiega|spiegami|analizza|'
    r'confronta|commenta|descrivi|summariz\w*|summary|analy[sz]\w*|explain|digest|synthesi[sz]\w*)\b',
    re.IGNORECASE,
)


def resolve_short_model_label(cfg: dict) -> str:
    """Extract a clean short model name from the active config for trace display."""
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


class LoopWatchdog:
    """
    Context manager keeping SSE/inference watchdog alive via silent heartbeat events.
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


def process_initial_vision(
    user_text: str,
    images: Optional[List[Any]],
    current_cfg: dict,
    emit_callback=None,
) -> Tuple[str, Optional[List[Any]]]:
    """Run VisionRouter on turn 1 if images are present and record the trace step."""
    if not images:
        return user_text, images

    try:
        from hecos.modules.web_ui.vision import VisionRouter
        try:
            from app.model_manager import ModelManager
        except ImportError:
            from hecos.app.model_manager import ModelManager

        btype, mname = ModelManager.get_effective_model_info(current_cfg)
        v_step = AgentTracer.start_step(
            kind="vision",
            label=tr("Analisi visiva immagini allegate", "Visual analysis of attached images"),
            args_preview=tr(f"{len(images)} immagine/i", f"{len(images)} image(s)"),
            icon="fa-eye",
            level="info",
            module_name="Vision AI",
        )
        user_text, images = VisionRouter.process_incoming_turn(
            user_text, images, mname, btype, emit_callback=emit_callback
        )
        AgentTracer.finish_step(v_step, status="ok")
    except Exception as _v_err:
        logger.debug(f"[AGENT] Vision routing exception: {_v_err}")

    return user_text, images


def eval_early_termination(
    user_text: str,
    accumulated_tool_results: List[Dict[str, Any]],
    extracted_text: Optional[str],
    state_manager: Any,
    images: Optional[List[Any]],
    iteration: int,
) -> Tuple[bool, str]:
    """
    Evaluate whether the agent already fulfilled user intent and can stop early.
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
        return out_str.lstrip().startswith(("Error:", "⚠️", "[SYSTEM ERROR"))

    has_search_card = any(
        (not _is_err(str(r.get("output", ""))))
        and (
            "[[HSEARCH:" in str(r.get("output", ""))
            or "[[HMEDIA:" in str(r.get("output", ""))
            or str(r.get("output", "")).lstrip().startswith(("📺 Tuned to", "⏹️ Live Stream stopped"))
        )
        for r in accumulated_tool_results
    )

    has_pending_vision_review = bool(images and len(images) > 0 and iteration == 1 and has_search_card)
    wants_synthesis = bool(_NETSEARCH_SYNTHESIS_INTENT_RE.search(user_text or ""))

    if has_generated_img and all_images_done and doc_satisfied:
        return True, tr("Immagine generata e risposta formulata", "Image generated and response formulated")

    if has_search_card and not has_pending_vision_review and doc_satisfied and has_text:
        if iteration == 1 and wants_synthesis:
            return False, ""
        return True, tr("Ricerca completata e risposta formulata", "Search completed and response formulated")

    return False, ""


def finalize_response(
    extracted_text: Optional[str],
    accumulated_tool_results: List[Dict[str, Any]],
    raw_response: Any,
    voice_status: bool,
    think_block: Optional[str] = None,
    missing_igen_detected: bool = False,
    unverified_file_notice: Optional[str] = None,
) -> Tuple[str, str]:
    """Standardize final response formatting across all loop termination paths."""
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

    verified_files = extract_verified_files_from_results(accumulated_tool_results)
    if verified_files:
        text = append_verified_file_links(text, verified_files)
    elif unverified_file_notice:
        text = f"{text.rstrip()}\n\n{unverified_file_notice}".strip()

    text = MediaInterceptor.append_ui_media_to_text(text, accumulated_tool_results)

    video_response, clean_voice = processore.clean_final_output(
        text, accumulated_tool_results, raw_response, voice_status
    )
    return video_response, clean_voice


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
    """Ensure final response, model metadata, and trace summary persist into SQLite history."""
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

        trace_to_save = (
            last_trace_summary
            if (last_trace_summary and agent_config.get("trace_persist_history", True))
            else None
        )
        model_info, _ = HistoryManager.enrich_model_info(
            LAST_PAYLOAD_INFO.get("model_info"),
            config=config,
            session_id=session_id,
            persona_name=clean_persona,
            trace_summary=trace_to_save,
        )

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
