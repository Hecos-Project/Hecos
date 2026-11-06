"""
hecos/core/agent/loop_guards.py
Modular guards, intent detectors, early-termination heuristics,
and lifecycle helpers for the Hecos Agentic Loop.
"""

import json
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
    has_text = bool(extracted_text and len(extracted_text.strip()) > 10)
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

    has_search_card = any(
        r.get("tag") == "NETSEARCH"
        or "[[HSEARCH:" in str(r.get("output", ""))
        or "[[HMEDIA:" in str(r.get("output", ""))
        for r in accumulated_tool_results
    )

    has_pending_vision_review = bool(images and len(images) > 0 and iteration == 1 and has_search_card)

    if has_generated_img and all_images_done and doc_satisfied and has_text:
        return True, tr(
            "Immagine generata e risposta formulata",
            "Image generated and response formulated",
        )

    if has_search_card and not has_pending_vision_review and doc_satisfied and has_text:
        return True, tr(
            "Ricerca completata e risposta formulata",
            "Search completed and response formulated",
        )

    return False, ""


# --- 5. RESPONSE FINALIZATION & SAFETY FORMATTER ---

def finalize_response(
    extracted_text: Optional[str],
    accumulated_tool_results: List[Dict[str, Any]],
    raw_response: Any,
    voice_status: bool,
    think_block: Optional[str] = None,
    missing_igen_detected: bool = False,
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
) -> None:
    """Ensures final response and trace summary are persisted into SQLite history."""
    try:
        from hecos.memory import brain_interface
        from hecos.core.llm.client import LAST_PAYLOAD_INFO

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

