"""
hecos/core/agent/loop.py
Hecos Phase 2 - Agentic Loop Orchestrator.
Orchestrates the multi-turn connection between Brain and Tools.
"""

import json
from typing import Any, Dict, List, Optional, Tuple

from hecos.core.logging import logger
from hecos.core.llm import brain
from hecos.core.agent.traces import AgentTracer, get_agent_config
from hecos.core.agent.trace_labeler import tr
from hecos.core.processing import processore

from hecos.core.agent.direct_commands import CommandInterceptor
from hecos.core.agent.media_interceptor import MediaInterceptor
from hecos.core.agent.loop_guards import (
    LoopWatchdog,
    is_uninstalled_image_gen_request,
    emit_missing_image_gen_warning,
    resolve_short_model_label,
    process_initial_vision,
    eval_early_termination,
    finalize_response,
    sync_assistant_history,
    extract_verified_files_from_results,
    are_executor_write_tools_enabled,
    is_executor_anti_hallucination_enabled,
    detect_unexecuted_file_claim,
    LoopStagnationTracker,
)


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
    so local models (e.g. 14B on 16k ctx) do not overflow, stall in KV thrash, or
    get silently left-truncated by Ollama. Returns number of compacted/trimmed messages.
    """
    if not agent_context:
        return 0

    num_ctx = _resolve_effective_num_ctx(cfg)
    # Estimate ~3.2 chars/token; reserve headroom for system prompt (~8k chars) + schemas (~10k chars) + reply
    total_char_cap = max(14000, int(num_ctx * 0.78 * 3.2) - 18000)
    def _context_chars() -> int:
        return len(user_text or "") + sum(len(str(m.get("content") or "")) for m in agent_context)

    if _context_chars() <= total_char_cap:
        return 0

    changed = compact_agent_context_tool_messages(agent_context, keep_recent=2, min_chars_to_compact=260)
    if _context_chars() <= total_char_cap:
        return changed

    # Condense verbose older assistant messages while always preserving the latest assistant turn
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

    # Final safety trim: drop oldest turns paired with trailing tool messages while keeping >= 4 entries
    while len(agent_context) > 4 and _context_chars() > total_char_cap:
        removed = agent_context.pop(0)
        if isinstance(removed, dict) and removed.get("role") == "assistant":
            while len(agent_context) > 4 and isinstance(agent_context[0], dict) and agent_context[0].get("role") == "tool":
                agent_context.pop(0)
        changed += 1

    return changed


class AgentExecutor:
    """
    Hecos Phase 2 - Agentic Loop.
    Executes autonomous multi-turn reasoning, tool calling, and response synthesis.
    """

    def __init__(
        self,
        config=None,
        config_manager=None,
        state_manager=None,
        max_iterations=None,
        trace_callback=None,
        current_user_id: str = "admin",
        current_user_role: str = "admin",
        session_id: Optional[str] = None,
        sender_tab_id: Optional[str] = None,
    ):
        self.config = config
        self.config_manager = config_manager
        self.state_manager = state_manager
        self.current_user_id = current_user_id
        self.current_user_role = current_user_role
        self.session_id = session_id
        self.sender_tab_id = sender_tab_id
        self.trace_callback = trace_callback
        self.last_trace_summary: Optional[dict] = None

        # Load cached agent configuration
        self.agent_config = get_agent_config()
        self._explicit_max_iterations = max_iterations is not None
        self.max_iterations = (
            max_iterations
            if max_iterations is not None
            else self.agent_config.get("max_iterations", 15)
        )
        self.is_enabled = self.agent_config.get("enabled", True)

    def _emit(self, msg: Any, level: str = "info") -> None:
        """Emits a trace through the unified AgentTracer session."""
        AgentTracer.emit(self.state_manager, msg, level=level)

    def _finalize_and_store_trace(self, final_msg: Optional[str] = None, status: str = "ok") -> None:
        """Finalizes the turn trace timeline and stores it for history and SSE clients."""
        try:
            self.last_trace_summary = AgentTracer.finalize_turn(final_msg, status=status)
            from hecos.core.llm.client import LAST_PAYLOAD_INFO
            LAST_PAYLOAD_INFO["agent_trace"] = self.last_trace_summary
        except Exception as e:
            logger.debug(f"[AGENT] finalize_turn error: {e}")

    def _sync_assistant_history(
        self,
        video_response: str,
        think_block: Optional[str] = None,
        user_text: Optional[str] = None,
    ) -> None:
        """Persists the turn's response and trace summary to the database."""
        sync_assistant_history(
            config=self.config,
            current_user_id=self.current_user_id,
            session_id=self.session_id,
            sender_tab_id=self.sender_tab_id,
            agent_config=self.agent_config,
            last_trace_summary=self.last_trace_summary,
            video_response=video_response,
            think_block=think_block,
            user_text=user_text,
        )

    def _sync_telemetry(self) -> None:
        """Syncs token counts and active model info with StateManager."""
        if not self.state_manager:
            return
        try:
            from hecos.core.llm.client import LAST_PAYLOAD_INFO
            self.state_manager.last_model = LAST_PAYLOAD_INFO.get("model")
            self.state_manager.last_tokens_prompt = LAST_PAYLOAD_INFO.get("prompt_tokens", 0)
            self.state_manager.last_tokens_completion = LAST_PAYLOAD_INFO.get("completion_tokens", 0)
        except Exception as e:
            logger.debug(f"[AGENT] Telemetry sync error: {e}")

    def run_agentic_loop(
        self,
        user_text: str,
        voice_status: bool = False,
        images: Optional[List[Any]] = None,
    ) -> Tuple[str, str]:
        """
        Runs the full autonomous loop:
        1. Checks global direct commands.
        2. Sets up image limits and checks for missing packages.
        3. Iterates: LLM inference -> Tool extraction & execution -> Termination checks.
        """
        AgentTracer.bind(
            state_manager=self.state_manager,
            trace_callback=self.trace_callback,
            session_id=self.session_id,
        )

        # 1. Global direct commands interceptor
        intercepted, response_output = CommandInterceptor.intercept(user_text, self)
        if intercepted:
            self._finalize_and_store_trace(tr("Comando diretto completato", "Direct command completed"))
            return processore.clean_final_output(response_output, [], response_output, voice_status)

        if not self.is_enabled:
            logger.info("[AGENT] Agentic Loop is disabled in config. Running single iteration.")
            self.max_iterations = 1

        # 2. Turn limits & state guards
        try:
            from hecos.core.processing.tool_dispatcher import get_requested_image_limit
            if self.state_manager:
                self.state_manager.requested_image_limit = get_requested_image_limit(user_text)
                self.state_manager.total_images_in_turn = 0
                self.state_manager.image_gen_failed = False
        except Exception as _e:
            logger.debug(f"[AGENT] Failed to set image limit: {_e}")

        missing_igen_detected = is_uninstalled_image_gen_request(user_text)
        if missing_igen_detected:
            emit_missing_image_gen_warning()

        iteration = 0
        stream_hallucination_retries = 0
        file_hallucination_retries = 0
        netsearch_hallucination_retries = 0
        unverified_file_notice: Optional[str] = None
        stagnation_tracker = LoopStagnationTracker()
        agent_context: List[Dict[str, Any]] = []
        accumulated_tool_results: List[Dict[str, Any]] = []

        # 3. Autonomous Loop protected by background watchdog
        with LoopWatchdog(self.trace_callback):
            while iteration < self.max_iterations:
                if self.state_manager and getattr(self.state_manager, "webui_stop_requested", False):
                    self._finalize_and_store_trace(
                        tr("Operazione interrotta dall'utente", "Operation aborted by user"),
                        status="error",
                    )
                    break

                iteration += 1
                logger.info(f"[AGENT] --- Iteration {iteration}/{self.max_iterations} ---")

                # Persist turn history only once at loop completion (via sync_assistant_history)
                # so intermediate tool/prose iterations never duplicate inside PromptBuilder DB history.
                save_hist = False
                current_cfg = (
                    self.config
                    if getattr(self, "config", None)
                    else (
                        self.config_manager.config
                        if getattr(self, "config_manager", None)
                        else processore.current_config
                    )
                )

                # Turn 1: Emit Execution Mode Badge to Timeline (Native Tools vs Fast Direct Commands)
                if iteration == 1:
                    if not self._explicit_max_iterations and _is_coding_loop_active(current_cfg):
                        self.max_iterations = max(self.max_iterations, 25)
                    pctrl = current_cfg.get("payload_control", {})
                    send_tools = pctrl.get("send_tools", True)
                    disable_tools = current_cfg.get("disable_tools", False)

                    if disable_tools:
                        m_label = tr("Modalità: Solo Chat", "Mode: Chat Only")
                        m_detail = tr("Esecuzione tool disabilitata a livello di sistema", "Tool execution disabled by system")
                        m_icon = "fa-comments"
                    elif send_tools:
                        _tool_mode = str(pctrl.get("tool_selection_mode") or "all").strip().lower()
                        _selected_tools = pctrl.get("selected_tools") or []
                        m_label = (
                            tr("Modalità: Tool Selezionati", "Mode: Selected Tools")
                            if _tool_mode == "custom"
                            else tr("Modalità: Tool Calling Nativo", "Mode: Native Tool Calling")
                        )
                        try:
                            from hecos.core.system.module_docs import get_tools_schema as _gts
                            _schema_list = _gts(payload_control=pctrl, config=current_cfg) or []
                            _schema_count = len(_schema_list)
                        except Exception:
                            _schema_count = 0
                        m_detail = (
                            tr(f"{_schema_count} funzioni selezionate nel modello", f"{_schema_count} selected schemas loaded in model")
                            if _tool_mode == "custom"
                            else tr(f"{_schema_count} funzioni caricate nel modello", f"{_schema_count} function schemas loaded in model")
                        )
                        m_icon = "fa-toolbox"
                    else:
                        m_label = tr("Modalità: Comandi Rapidi (Fast Chat)", "Mode: Direct Commands (Fast Chat)")
                        m_detail = tr("Schemi JSON disattivati (~8k token risparmiati) · /img e /search attivi", "Tool schemas disabled (~8k tokens saved) · /img & /search active")
                        m_icon = "fa-bolt"

                    mode_step = AgentTracer.start_step(
                        kind="system",
                        label=m_label,
                        detail=m_detail,
                        icon=m_icon,
                        level="info",
                        module_name=tr("Configurazione Payload", "Payload Control"),
                        close_previous=False,
                    )
                    AgentTracer.finish_step(mode_step, status="ok", result_preview=m_detail)



                # Perception: Vision Routing on turn 1
                if images and iteration == 1:
                    user_text, images = process_initial_vision(
                        user_text, images, current_cfg, emit_callback=self._emit
                    )

                enforce_agent_context_budget(agent_context, current_cfg, user_text=user_text)

                model_short = resolve_short_model_label(current_cfg)
                llm_label = (
                    tr("Elaborazione richiesta", "Analyzing request & generating response")
                    if iteration == 1
                    else tr(f"Sintesi risultati ed elaborazione (Step {iteration})", f"Synthesizing tool results (Step {iteration})")
                )

                llm_step = AgentTracer.start_step(
                    kind="llm",
                    label=llm_label,
                    detail=model_short,
                    icon="fa-brain",
                    level="info",
                    module_name="AI Brain",
                )

                try:
                    raw_response = brain.generate_response(
                        user_text,
                        external_config=current_cfg,
                        agent_context=agent_context,
                        save_history=save_hist,
                        images=images,
                        user_id=self.current_user_id,
                        session_id=self.session_id,
                        sender_tab_id=self.sender_tab_id,
                    )
                except Exception as llm_exc:
                    AgentTracer.finish_step(llm_step, status="error", result_preview=str(llm_exc))
                    raise

                AgentTracer.finish_step(llm_step, status="ok")

                if self.state_manager and getattr(self.state_manager, "webui_stop_requested", False):
                    self._finalize_and_store_trace(
                        tr("Operazione interrotta dall'utente", "Operation aborted by user"),
                        status="error",
                    )
                    break

                # Extract and dispatch tools
                tools_called, tool_results, extracted_text, think_block = processore.extract_and_execute_tools(
                    raw_response, self.config, sm=self.state_manager
                )

                if think_block:
                    self._emit({"type": "think", "text": think_block}, level="think")

                self._sync_telemetry()

                # Case A: Plain text response (no further tools called)
                if not tools_called:
                    # Safeguard against text-mode LLMs mimicking '📺 Tuned to...' from history without calling a tool
                    _fake_stream_claim = any(
                        tok in (extracted_text or "")
                        for tok in ("📺 Tuned to", "Launched in VLC Desktop", "⏹️ Live Stream stopped")
                    )
                    _stream_tool_already_ran = any(
                        r.get("action") in ("stream_control", "stream_search")
                        or "📺 Tuned to" in str(r.get("output", ""))
                        or "Live Stream stopped" in str(r.get("output", ""))
                        for r in accumulated_tool_results
                    )
                    if (
                        _fake_stream_claim
                        and not _stream_tool_already_ran
                        and stream_hallucination_retries < 1
                        and iteration < self.max_iterations
                    ):
                        stream_hallucination_retries += 1
                        logger.warning(
                            "[AGENT] Caught unexecuted stream status badge hallucination — forcing tool retry."
                        )
                        llm_step["result_preview"] = tr(
                            "Rilevato falso stato streaming — richiamo il tool",
                            "Detected unexecuted stream badge — retrying tool call",
                        )
                        AgentTracer.update_step(llm_step, detail=llm_step["result_preview"])
                        agent_context.append({"role": "assistant", "content": str(raw_response or extracted_text or "")})
                        agent_context.append({
                            "role": "user",
                            "content": (
                                "[SYSTEM GUARD]: You wrote a fake '📺 Tuned to...' text line without actually calling any tool, "
                                "so VLC/player was NOT changed. Emit `NETSEARCH__stream_control(action='play', query='<requested channel>', category='tv')` "
                                "(or `/canale <channel>` on its own line) NOW to execute it for real."
                            ),
                        })
                        continue

                    # Safeguard against coding LLMs claiming edits/fixes without real disk writes,
                    # echoing <tool_response>, or parroting an old Loop Breaker error from history.
                    _verified_disk_files = extract_verified_files_from_results(accumulated_tool_results)
                    _write_actions = {"write_file", "patch_file", "run_aider_task", "git_restore", "move_path", "create_dir", "delete_file"}
                    _executor_mutated_disk = bool(_verified_disk_files) or any(
                        str(r.get("tag", "")).upper() == "EXECUTOR"
                        and str(r.get("action") or "") in _write_actions
                        and "SYNTAX ERROR" not in str(r.get("output", ""))
                        and "Path not found:" not in str(r.get("output", ""))
                        and "Text to replace not found" not in str(r.get("output", ""))
                        for r in accumulated_tool_results
                    )
                    _echoed_tool_resp = "<tool_response>" in str(raw_response or "").lower()
                    _parroted_loop_breaker = (
                        "Loop Breaker: Stopped after" in (extracted_text or "")
                        or ("> ⚠️" in (extracted_text or "") and "SYNTAX ERROR" in (extracted_text or ""))
                    )
                    if (
                        (
                            (not _executor_mutated_disk and not _verified_disk_files and detect_unexecuted_file_claim(extracted_text))
                            or (_echoed_tool_resp and not _verified_disk_files)
                            or _parroted_loop_breaker
                        )
                        and is_executor_anti_hallucination_enabled(current_cfg)
                    ):
                        if are_executor_write_tools_enabled(current_cfg):
                            if file_hallucination_retries < 2 and iteration < self.max_iterations:
                                file_hallucination_retries += 1
                                logger.warning(
                                    "[AGENT] Caught unexecuted EXECUTOR claim / <tool_response> / Loop Breaker parrot — forcing real EXECUTOR tool retry."
                                )
                                llm_step["result_preview"] = tr(
                                    "Rilevata risposta simulata — richiamo EXECUTOR",
                                    "Detected unexecuted claim or echoed error — retrying EXECUTOR",
                                )
                                AgentTracer.update_step(llm_step, detail=llm_step["result_preview"])
                                agent_context.append({"role": "assistant", "content": str(raw_response or extracted_text or "")})
                                if _echoed_tool_resp:
                                    guard_content = (
                                        "[SYSTEM GUARD]: Do NOT echo `<tool_response>` text! Output real tool calls only. "
                                        "Invoke `EXECUTOR__run_aider_task` or write ONE concise file per turn via `EXECUTOR__write_file` "
                                        "(with forward slashes `/` in Windows paths) right now."
                                    )
                                elif _parroted_loop_breaker:
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
                                agent_context.append({"role": "user", "content": guard_content})
                                continue
                            else:
                                unverified_file_notice = (
                                    "> ⚠️ **System Notice:** No files were actually written or modified on disk in this turn "
                                    "(no `EXECUTOR` tool was invoked)."
                                )
                        else:
                            unverified_file_notice = (
                                "> ⚠️ **System Notice:** No files were written to disk because filesystem write tools "
                                "(`EXECUTOR__write_file` / `patch_file`) are disabled in Payload & Tools Control."
                            )

                    # Safeguard against LLMs answering web/media search requests from memory without invoking NETSEARCH
                    from hecos.core.agent.loop_guards import (
                        are_netsearch_tools_enabled,
                        detect_unexecuted_netsearch_request,
                        get_netsearch_unexecuted_guard_message,
                    )
                    _netsearch_already_ran = any(
                        str(r.get("tag", "")).upper() in ("NETSEARCH", "SLASH_COMMAND")
                        or "[[HSEARCH:" in str(r.get("output", ""))
                        or "[[HMEDIA:" in str(r.get("output", ""))
                        for r in accumulated_tool_results
                    )
                    if (
                        not _netsearch_already_ran
                        and netsearch_hallucination_retries < 1
                        and iteration < self.max_iterations
                        and are_netsearch_tools_enabled(current_cfg)
                        and detect_unexecuted_netsearch_request(user_text, extracted_text)
                    ):
                        _guard_msg = get_netsearch_unexecuted_guard_message()
                        if _guard_msg:
                            netsearch_hallucination_retries += 1
                            logger.warning(
                                "[AGENT] Caught unexecuted Net Search request — forcing real search tool retry."
                            )
                            llm_step["result_preview"] = tr(
                                "Ricerca non eseguita — richiamo Net Search",
                                "Search skipped — retrying with Net Search",
                            )
                            AgentTracer.update_step(llm_step, detail=llm_step["result_preview"])
                            agent_context.append({"role": "assistant", "content": str(raw_response or extracted_text or "")})
                            agent_context.append({"role": "user", "content": _guard_msg})
                            continue

                    llm_step["result_preview"] = tr("Risposta formulata", "Response formulated")
                    self._finalize_and_store_trace(tr("Risposta formulata", "Response formulated"), status="ok")

                    video_response, clean_voice = finalize_response(
                        extracted_text=extracted_text,
                        accumulated_tool_results=accumulated_tool_results,
                        raw_response=raw_response,
                        voice_status=voice_status,
                        think_block=think_block,
                        missing_igen_detected=missing_igen_detected,
                        unverified_file_notice=unverified_file_notice,
                    )
                    self._sync_assistant_history(video_response, think_block, user_text=user_text)
                    return video_response, clean_voice

                # Case B: Tools were triggered
                called_tags = ", ".join(sorted({str(r.get("tag", "")) for r in tool_results if r.get("tag")}))
                if called_tags:
                    llm_step["result_preview"] = tr(f"Attivazione: {called_tags}", f"Triggered: {called_tags}")

                if hasattr(raw_response, 'role'):
                    if hasattr(raw_response, 'model_dump'):
                        agent_context.append(raw_response.model_dump())
                    elif hasattr(raw_response, 'dict'):
                        agent_context.append(raw_response.dict())
                    else:
                        agent_context.append(json.loads(json.dumps(raw_response, default=lambda o: o.__dict__)))
                else:
                    agent_context.append({"role": "assistant", "content": str(raw_response)})

                accumulated_tool_results.extend(tool_results)
                for res in tool_results:
                    if self.state_manager:
                        self.state_manager.last_tool = res.get("tag")

                    output_text = res.get("output")

                    if MediaInterceptor.check_webcam_short_circuit(output_text):
                        self._finalize_and_store_trace(
                            tr("Richiesta fotocamera inviata al browser", "Camera request forwarded to browser"),
                            status="ok",
                        )
                        camera_resp = "Sure! [CAMERA_SNAPSHOT_REQUEST] Please take the photo when prompted by your browser."
                        video_response, clean_voice = processore.clean_final_output(camera_resp, tool_results, camera_resp, voice_status)
                        self._sync_assistant_history(video_response, user_text=user_text)
                        return video_response, clean_voice

                    agent_context.append({
                        "role": "tool",
                        "tool_call_id": res.get("id"),
                        "name": res.get("tag"),
                        "content": output_text,
                    })

                    images = MediaInterceptor.load_vision_images(output_text, images, self._emit)
                    images = MediaInterceptor.load_search_vision_images(output_text, images, self._emit)

                compact_agent_context_tool_messages(agent_context, keep_recent=3)

                stagnation_decision, stagnation_msg, _ = stagnation_tracker.step(tool_results)
                if stagnation_decision == "nudge" and iteration < self.max_iterations:
                    logger.warning(f"[AGENT] Loop breaker nudge triggered at iteration {iteration}/{self.max_iterations}")
                    nudge_step = AgentTracer.start_step(
                        kind="system",
                        label=tr("Loop ripetitivo — cambio strategia", "Repetitive loop — forcing strategy change"),
                        icon="fa-rotate-left",
                        level="warning",
                        module_name="Loop Breaker",
                    )
                    AgentTracer.finish_step(nudge_step, status="ok", result_preview=stagnation_msg[:180])
                    agent_context.append({"role": "user", "content": stagnation_msg})
                    continue

                if stagnation_decision == "break":
                    logger.warning(f"[AGENT] Repetitive loop broken early at iteration {iteration}/{self.max_iterations}: {stagnation_msg}")
                    brk_step = AgentTracer.start_step(
                        kind="error",
                        label=tr("Loop ripetitivo interrotto", "Repetitive loop aborted early"),
                        icon="fa-hand",
                        level="error",
                        module_name="Loop Breaker",
                    )
                    AgentTracer.finish_step(brk_step, status="error", result_preview=stagnation_msg[:180])
                    self._finalize_and_store_trace(
                        tr("Loop ripetitivo interrotto in anticipo", "Repetitive no-progress loop broken early"),
                        status="error",
                    )
                    combined_text = f"{(extracted_text or '').strip()}\n\n{stagnation_msg}".strip()
                    video_response, clean_voice = finalize_response(
                        extracted_text=combined_text,
                        accumulated_tool_results=accumulated_tool_results,
                        raw_response=raw_response,
                        voice_status=voice_status,
                        think_block=think_block,
                        missing_igen_detected=missing_igen_detected,
                    )
                    self._sync_assistant_history(video_response, think_block, user_text=user_text)
                    return video_response, clean_voice

                # Check early termination (e.g., image generated or search cards completed)
                should_short, reason = eval_early_termination(
                    user_text=user_text,
                    accumulated_tool_results=accumulated_tool_results,
                    extracted_text=extracted_text,
                    state_manager=self.state_manager,
                    images=images,
                    iteration=iteration,
                )
                if should_short:
                    self._finalize_and_store_trace(reason, status="ok")
                    video_response, clean_voice = finalize_response(
                        extracted_text=extracted_text,
                        accumulated_tool_results=accumulated_tool_results,
                        raw_response=raw_response,
                        voice_status=voice_status,
                        think_block=think_block,
                        missing_igen_detected=missing_igen_detected,
                    )
                    self._sync_assistant_history(video_response, think_block, user_text=user_text)
                    return video_response, clean_voice

                # Max iterations limit safeguard
                if iteration == self.max_iterations:
                    logger.warning(
                        f"[AGENT] Maximum thought iterations ({self.max_iterations}) reached — returning best available response."
                    )
                    self._finalize_and_store_trace(
                        tr("Limite iterazioni raggiunto — invio risposta", "Iteration limit reached — returning response"),
                        status="ok",
                    )
                    video_response, clean_voice = finalize_response(
                        extracted_text=extracted_text,
                        accumulated_tool_results=accumulated_tool_results,
                        raw_response=raw_response,
                        voice_status=voice_status,
                        think_block=think_block,
                        missing_igen_detected=missing_igen_detected,
                    )
                    self._sync_assistant_history(video_response, think_block, user_text=user_text)
                    return video_response, clean_voice

        # Fallback if loop was interrupted without reaching return
        video_response, clean_voice = finalize_response(
            extracted_text=None,
            accumulated_tool_results=accumulated_tool_results,
            raw_response="",
            voice_status=voice_status,
        )
        self._sync_assistant_history(video_response, user_text=user_text)
        return video_response, clean_voice
