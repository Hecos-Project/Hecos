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

_MESSENGER_SEND_INTENT_RE = re.compile(
    r'(?:\b(?:whatsapp|wazzap|telegram)\b'
    r'|\b(?:invia\w*|manda\w*|spedisc\w*|inoltra\w*|send|forward)\b'
    r'[^\r\n]{0,45}\b(?:su|via|tramite|al\s+mio\s+numero|al\s+mio\s+contatto|on|to)\b)',
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

    wants_messenger = bool(_MESSENGER_SEND_INTENT_RE.search(user_text or ""))
    has_messenger_sent = any(
        str(r.get("tag", "")).upper() == "MESSENGER"
        and ("✅" in str(r.get("output", "")) or "⚠️" in str(r.get("output", "")))
        for r in accumulated_tool_results
    )
    messenger_satisfied = (not wants_messenger) or has_messenger_sent

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

    if has_generated_img and all_images_done and doc_satisfied and messenger_satisfied:
        exec_plan_id = str(getattr(state_manager, "active_execute_plan_id", "") or "").strip() if state_manager else ""
        single_step_idx = int(getattr(state_manager, "active_execute_single_step", 0) or 0) if state_manager else 0
        img_failed = bool(getattr(state_manager, "image_gen_failed", False)) if state_manager else False
        plan_allows_early_stop = True
        if exec_plan_id and not img_failed:
            try:
                from hecos.core.action_plans import get_action_plan_manager
                plan = get_action_plan_manager().resolve_plan(plan_id=exec_plan_id)
                if plan:
                    steps = plan.get("steps") or []
                    if single_step_idx > 0:
                        target_step = next(
                            (s for s in steps if int(s.get("index") or 0) == single_step_idx),
                            None,
                        )
                        if target_step and target_step.get("status") not in ("done", "skipped"):
                            plan_allows_early_stop = False
                    elif any(s.get("status") not in ("done", "skipped") for s in steps):
                        plan_allows_early_stop = False
            except Exception:
                pass
        if plan_allows_early_stop:
            return True, tr("Immagine generata e risposta formulata", "Image generated and response formulated")

    if has_search_card and not has_pending_vision_review and doc_satisfied and messenger_satisfied and has_text:
        if iteration == 1 and wants_synthesis:
            return False, ""
        return True, tr("Ricerca completata e risposta formulata", "Search completed and response formulated")

    # Early termination as soon as Plan-Only (Architect) mode created or revised the Action Plan
    has_plan_only_created = any(
        str(r.get("tag", "")).upper() == "ACTION_PLANS"
        and (
            "[ACTION_PLAN CREATED — PLAN-ONLY MODE]" in str(r.get("output", ""))
            or "[ACTION_PLAN REVISED — PLAN-ONLY MODE]" in str(r.get("output", ""))
        )
        for r in accumulated_tool_results
    )
    if has_plan_only_created:
        is_revised = any(
            "[ACTION_PLAN REVISED — PLAN-ONLY MODE]" in str(r.get("output", ""))
            for r in accumulated_tool_results
        )
        if is_revised:
            return True, tr("Piano d'azione aggiornato (Modalità Architetto)", "Action Plan revised (Architect Mode)")
        return True, tr("Piano d'azione creato (Modalità Architetto)", "Action Plan created (Architect Mode)")

    return False, ""


def _extract_plan_only_payload(accumulated_tool_results: List[Dict[str, Any]]) -> Tuple[str, Dict[str, Any], bool]:
    """Extract (markdown_body, meta_dict, is_revised) from Plan-Only create_plan/revise_plan tool results."""
    import json as _json

    for r in reversed(accumulated_tool_results or []):
        if str(r.get("tag", "")).upper() != "ACTION_PLANS":
            continue
        raw_out = str(r.get("output", ""))
        marker = ""
        is_revised = False
        if "[ACTION_PLAN REVISED — PLAN-ONLY MODE]" in raw_out:
            marker = "[ACTION_PLAN REVISED — PLAN-ONLY MODE]"
            is_revised = True
        elif "[ACTION_PLAN CREATED — PLAN-ONLY MODE]" in raw_out:
            marker = "[ACTION_PLAN CREATED — PLAN-ONLY MODE]"
            is_revised = False
        if not marker:
            continue

        body = raw_out.split(marker, 1)[1].split("[SYSTEM:", 1)[0].strip()
        meta: Dict[str, Any] = {}
        meta_m = re.match(r"^<!--PLAN_META:(\{.*?\})-->\s*", body, flags=re.DOTALL)
        if meta_m:
            try:
                parsed = _json.loads(meta_m.group(1))
                if isinstance(parsed, dict):
                    meta = parsed
            except Exception:
                meta = {}
            body = body[meta_m.end():].strip()
        return body, meta, is_revised
    return "", {}, False


def _build_plan_voice_summary(meta: Dict[str, Any], is_revised: bool) -> str:
    """Create a concise spoken TTS summary for an Implementation Plan instead of reading markdown/code aloud."""
    title = str(meta.get("title") or "").strip()
    steps_count = int(meta.get("steps_count") or 0)
    rev = int(meta.get("revision") or 1)
    is_it = str(getattr(translator.get_translator(), "language", "en") or "en").lower().startswith("it")

    if is_it:
        title_part = f" per {title}" if title else ""
        steps_part = f", con {steps_count} passaggi" if steps_count else ""
        if is_revised:
            return f"Piano di implementazione aggiornato alla revisione {rev}{title_part}{steps_part}. Puoi controllare le modifiche o avviarlo con Esegui Piano."
        return f"Piano di implementazione pronto{title_part}{steps_part}. Puoi revisionarlo o avviarlo con Esegui Piano."
    else:
        title_part = f" for {title}" if title else ""
        steps_part = f", with {steps_count} steps" if steps_count else ""
        if is_revised:
            return f"Implementation plan updated to revision {rev}{title_part}{steps_part}. Review the updates or click Execute Plan."
        return f"Implementation plan ready{title_part}{steps_part}. You can review, revise, or run it with Execute Plan."


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
    plan_only_out, plan_meta, plan_is_revised = _extract_plan_only_payload(accumulated_tool_results)
    plan_voice_override = ""

    if plan_only_out:
        is_it = str(getattr(translator.get_translator(), "language", "en") or "en").lower().startswith("it")
        rev = int(plan_meta.get("revision") or 1)
        if is_it:
            badge_hdr = (
                f"📋 **Piano di Implementazione Aggiornato (v{rev})**"
                if plan_is_revised
                else "📋 **Piano di Implementazione Pronto**"
            )
            footer = (
                "> 💡 **Pronto per la revisione:** clicca **📄 Vedi Piano** per la vista completa, "
                "usa **✏️ Revisiona** (o `/plan revise <modifiche>`) per aggiornare il piano, "
                "oppure scegli un modello in **Run with Coder** e clicca **▶️ Esegui Piano** (o `/code`)."
            )
        else:
            badge_hdr = (
                f"📋 **Implementation Plan Updated (v{rev})**"
                if plan_is_revised
                else "📋 **Implementation Plan Ready**"
            )
            footer = (
                "> 💡 **Ready for review:** click **📄 View Plan** for the full blueprint, "
                "use **✏️ Revise** (or `/plan revise <changes>`) to refine it, "
                "or choose a model in **Run with Coder** and click **▶️ Execute Plan** (or `/code`)."
            )

        clean_existing = text.strip()
        # Display full rich Implementation Plan when model emitted only a tool call or brief preamble
        if not clean_existing or (len(plan_only_out) > len(clean_existing) + 120 and "#" in plan_only_out):
            preamble = f"{clean_existing}\n\n---\n\n" if (clean_existing and len(clean_existing) <= 280) else ""
            text = f"{badge_hdr}\n\n{preamble}{plan_only_out}\n\n{footer}"
        elif footer not in clean_existing:
            text = f"{clean_existing}\n\n{footer}"

        if voice_status:
            plan_voice_override = _build_plan_voice_summary(plan_meta, plan_is_revised)

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
    if voice_status and plan_voice_override:
        clean_voice = plan_voice_override
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
