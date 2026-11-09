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
)


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

    def _sync_assistant_history(self, video_response: str, think_block: Optional[str] = None) -> None:
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

                save_hist = (iteration == 1)
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
                    pctrl = current_cfg.get("payload_control", {})
                    send_tools = pctrl.get("send_tools", True)
                    disable_tools = current_cfg.get("disable_tools", False)

                    if disable_tools:
                        m_label = tr("Modalità: Solo Chat", "Mode: Chat Only")
                        m_detail = tr("Esecuzione tool disabilitata a livello di sistema", "Tool execution disabled by system")
                        m_icon = "fa-comments"
                    elif send_tools:
                        m_label = tr("Modalità: Tool Calling Nativo", "Mode: Native Tool Calling")
                        try:
                            from hecos.core.system.module_docs import get_tools_schema as _gts
                            _schema_count = len(_gts())
                        except Exception:
                            _schema_count = 0
                        m_detail = tr(f"{_schema_count} funzioni caricate nel modello", f"{_schema_count} function schemas loaded in model")
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
                    llm_step["result_preview"] = tr("Risposta formulata", "Response formulated")
                    self._finalize_and_store_trace(tr("Risposta formulata", "Response formulated"), status="ok")

                    video_response, clean_voice = finalize_response(
                        extracted_text=extracted_text,
                        accumulated_tool_results=accumulated_tool_results,
                        raw_response=raw_response,
                        voice_status=voice_status,
                        think_block=think_block,
                        missing_igen_detected=missing_igen_detected,
                    )
                    self._sync_assistant_history(video_response, think_block)
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
                        return video_response, clean_voice

                    agent_context.append({
                        "role": "tool",
                        "tool_call_id": res.get("id"),
                        "name": res.get("tag"),
                        "content": output_text,
                    })

                    images = MediaInterceptor.load_vision_images(output_text, images, self._emit)
                    images = MediaInterceptor.load_search_vision_images(output_text, images, self._emit)

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
                    self._sync_assistant_history(video_response, think_block)
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
                    self._sync_assistant_history(video_response, think_block)
                    return video_response, clean_voice

        # Fallback if loop was interrupted without reaching return
        video_response, clean_voice = finalize_response(
            extracted_text=None,
            accumulated_tool_results=accumulated_tool_results,
            raw_response="",
            voice_status=voice_status,
        )
        return video_response, clean_voice
