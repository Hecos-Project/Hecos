"""
hecos/core/agent/loop.py
Hecos Phase 2 - Agentic Loop Orchestrator.
Orchestrates the multi-turn connection between Brain and Tools.
"""

import json
from typing import Any, Dict, List, Optional, Tuple

import hecos.core.agent.loop_guards as loop_guards
from hecos.core.logging import logger
from hecos.core.llm import brain
from hecos.core.agent.traces import AgentTracer, get_agent_config
from hecos.core.agent.trace_labeler import tr
from hecos.core.processing import processore

from hecos.core.agent.direct_commands import CommandInterceptor
from hecos.core.agent.media_interceptor import MediaInterceptor
from hecos.core.agent.checkpointing import (
    build_resume_state,
    mark_checkpoint_status,
    save_turn_checkpoint,
)
from hecos.core.agent.context_budget import (  # noqa: F401 (re-exported for callers & tests)
    _is_coding_loop_active,
    compact_agent_context_tool_messages,
    _resolve_effective_num_ctx,
    enforce_agent_context_budget,
)
from hecos.core.agent.loop_guards import (
    LoopWatchdog,
    LoopStagnationTracker,
    is_uninstalled_image_gen_request,
    emit_missing_image_gen_warning,
    resolve_short_model_label,
    process_initial_vision,
    evaluate_plain_text_guards,
    eval_early_termination,
    finalize_response,
    sync_assistant_history,
    is_llm_error_response,
)

_ORIG_SYNC_ASSISTANT_HISTORY = sync_assistant_history


def _append_raw_assistant_context(agent_context: List[Dict[str, Any]], raw_response: Any) -> None:
    """Append the model's raw assistant message (including native tool_calls) into `agent_context`."""
    if hasattr(raw_response, "role"):
        if hasattr(raw_response, "model_dump"):
            agent_context.append(raw_response.model_dump())
        elif hasattr(raw_response, "dict"):
            agent_context.append(raw_response.dict())
        else:
            agent_context.append(json.loads(json.dumps(raw_response, default=lambda o: o.__dict__)))
    else:
        agent_context.append({"role": "assistant", "content": str(raw_response)})


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
        cancel_event=None,
        turn_id: Optional[str] = None,
    ):
        self.config = config
        self.config_manager = config_manager
        self.state_manager = state_manager
        self.current_user_id = current_user_id
        self.current_user_role = current_user_role
        self.session_id = session_id
        self.sender_tab_id = sender_tab_id
        self.trace_callback = trace_callback
        self.cancel_event = cancel_event
        self.turn_id = turn_id
        self.last_trace_summary: Optional[dict] = None

        self.agent_config = get_agent_config()
        self._explicit_max_iterations = max_iterations is not None
        self.max_iterations = (
            max_iterations
            if max_iterations is not None
            else self.agent_config.get("max_iterations", 15)
        )
        self.is_enabled = self.agent_config.get("enabled", True)

    def _is_superseded(self) -> bool:
        try:
            from hecos.core.agent.turn_control import is_turn_superseded
            return is_turn_superseded(self.session_id, self.turn_id)
        except Exception:
            return False

    def _is_cancelled(self) -> bool:
        if self.cancel_event is not None and self.cancel_event.is_set():
            return True
        if self._is_superseded():
            return True
        if self.cancel_event is None and self.state_manager and getattr(self.state_manager, "webui_stop_requested", False):
            return True
        return False

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
        sync_fn = (
            sync_assistant_history
            if sync_assistant_history is not _ORIG_SYNC_ASSISTANT_HISTORY
            else loop_guards.sync_assistant_history
        )
        sync_fn(
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

    def _resolve_current_cfg(self) -> Dict[str, Any]:
        """Resolve the active configuration dict for the current iteration."""
        if getattr(self, "config", None):
            return self.config
        if getattr(self, "config_manager", None):
            return self.config_manager.config
        return processore.current_config

    def _emit_mode_step(self, current_cfg: Dict[str, Any]) -> None:
        """Apply turn-1 coding budget extension and emit the Execution Mode Badge to the trace timeline."""
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
            # Check if Ollama native tool API is bypassed for Gemma 4 text-mode models
            is_gemma4_text_mode = False
            try:
                from hecos.core.llm.params_builder import resolve_backend_and_model, _is_gemma4_model
                _btype, _mname, _spec_cfg = resolve_backend_and_model(current_cfg)
                if _btype == "ollama" and _mname:
                    _api_url = _spec_cfg.get("url", "http://127.0.0.1:11434")
                    is_gemma4_text_mode = bool(_is_gemma4_model(_mname, _api_url))
            except Exception:
                is_gemma4_text_mode = False

            if is_gemma4_text_mode:
                m_label = tr("Modalità: Tool Calling Testuale (Gemma 4)", "Mode: Text-Mode Tool Calling (Gemma 4)")
                m_detail = tr(
                    "Chiamate testuali & comandi rapidi attivi (API tool nativa disabilitata per Gemma 4)",
                    "Text-mode module calls & slash commands active (native tool API disabled for Gemma 4)",
                )
                m_icon = "fa-terminal"
            else:
                tool_mode = str(pctrl.get("tool_selection_mode") or "all").strip().lower()
                m_label = (
                    tr("Modalità: Tool Selezionati", "Mode: Selected Tools")
                    if tool_mode == "custom"
                    else tr("Modalità: Tool Calling Nativo", "Mode: Native Tool Calling")
                )
                try:
                    from hecos.core.system.module_docs import get_tools_schema as _gts
                    schema_count = len(_gts(payload_control=pctrl, config=current_cfg) or [])
                except Exception:
                    schema_count = 0
                m_detail = (
                    tr(f"{schema_count} funzioni selezionate nel modello", f"{schema_count} selected schemas loaded in model")
                    if tool_mode == "custom"
                    else tr(f"{schema_count} funzioni caricate nel modello", f"{schema_count} function schemas loaded in model")
                )
                m_icon = "fa-toolbox"
        else:
            m_label = tr("Modalità: Comandi Rapidi (Fast Chat)", "Mode: Direct Commands (Fast Chat)")
            m_detail = tr(
                "Schemi JSON disattivati (~8k token risparmiati) · /img e /search attivi",
                "Tool schemas disabled (~8k tokens saved) · /img & /search active",
            )
            m_icon = "fa-bolt"

        mode_step = AgentTracer.start_step(
            kind="system",
            label=m_label,
            detail=m_detail,
            icon=m_icon,
            level="info",
            module_name=tr("Configurazione Payload", "Payload Control"),
            close_previous=False,
            print_cli=False,
        )
        AgentTracer.finish_step(mode_step, status="ok", result_preview=m_detail)

        # Emit an unmistakable 0ms Architect Mode badge whenever Plan First or Plan Revision is active
        try:
            _is_exec_turn = bool(current_cfg.get("_turn_execute_plan") or current_cfg.get("_turn_fast_code"))
            _rev_pid = str(current_cfg.get("_turn_revise_plan_id") or "").strip()
            _ap_cfg_mode = str((current_cfg.get("plugins") or {}).get("ACTION_PLANS", {}).get("plan_mode") or "").lower()
            _is_plan_first = bool(current_cfg.get("_turn_plan_only")) or (not _is_exec_turn and _ap_cfg_mode == "plan_only")
            if _rev_pid:
                _arch_detail = tr(
                    "Aggiornamento Piano di Implementazione (sola lettura · tool mutanti bloccati)",
                    "Revising Implementation Plan (read-only · mutating tools blocked)",
                )
                _arch_step = AgentTracer.start_step(
                    kind="system",
                    label=tr("Modalità Architetto · Revisione Piano", "Architect Mode · Plan Revision"),
                    detail=_arch_detail,
                    icon="fa-pen-to-square",
                    level="info",
                    module_name=tr("Action Plan", "Action Plan"),
                    close_previous=False,
                )
                AgentTracer.finish_step(_arch_step, status="ok", result_preview=_arch_detail)
            elif _is_plan_first:
                _arch_detail = tr(
                    "Generazione Piano di Implementazione senza modifica file (tool mutanti bloccati)",
                    "Generating Implementation Plan without file edits (mutating tools blocked)",
                )
                _arch_step = AgentTracer.start_step(
                    kind="system",
                    label=tr("Modalità Architetto · Plan First", "Architect Mode · Plan First"),
                    detail=_arch_detail,
                    icon="fa-list-check",
                    level="info",
                    module_name=tr("Action Plan", "Action Plan"),
                    close_previous=False,
                )
                AgentTracer.finish_step(_arch_step, status="ok", result_preview=_arch_detail)
        except Exception:
            pass

    def _conclude_turn(
        self,
        *,
        trace_message: Optional[str],
        trace_status: str = "ok",
        extracted_text: Optional[str],
        accumulated_tool_results: List[Dict[str, Any]],
        raw_response: Any,
        voice_status: bool,
        think_block: Optional[str] = None,
        missing_igen_detected: bool = False,
        unverified_file_notice: Optional[str] = None,
        user_text: Optional[str] = None,
    ) -> Tuple[str, str]:
        """Finalize trace, format response, persist DB history, and return (video_response, clean_voice)."""
        if trace_message is not None:
            self._finalize_and_store_trace(trace_message, status=trace_status)
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
        self._finalize_checkpoint(trace_status=trace_status, trace_message=trace_message, extracted_text=extracted_text)
        return video_response, clean_voice

    def _persist_checkpoint(
        self,
        *,
        user_text: str,
        iteration: int,
        agent_context: List[Dict[str, Any]],
        accumulated_tool_results: List[Dict[str, Any]],
        retries_state: Dict[str, int],
        current_cfg: Optional[Dict[str, Any]] = None,
        status: str = "running",
        reason: str = "",
    ) -> None:
        """Persist turn progress safely so crashes/timeouts can resume from the last step."""
        if not self.session_id or self._is_cancelled():
            return
        try:
            from hecos.core.action_plans import get_action_plans_config, get_action_plan_manager
            ap_cfg = get_action_plans_config(cfg_mgr=self.config_manager, raw_config=current_cfg or self.config)
            if not ap_cfg.get("checkpoint_enabled", True):
                return
            linked = get_action_plan_manager().resolve_plan(source_id=self.session_id)
            plan_id = str((linked or {}).get("plan_id") or "")
        except Exception:
            plan_id = ""

        try:
            save_turn_checkpoint(
                session_id=self.session_id,
                user_text=user_text,
                user_id=self.current_user_id,
                iteration=iteration,
                max_iterations=self.max_iterations,
                agent_context=agent_context,
                accumulated_tool_results=accumulated_tool_results,
                retries_state=retries_state,
                status=status,
                reason=reason,
                model_label=resolve_short_model_label(current_cfg) if current_cfg else "",
                plan_id=plan_id,
            )
        except Exception as _ce:
            logger.debug(f"[AGENT] Checkpoint save skipped: {_ce}")

    def _finalize_checkpoint(
        self,
        *,
        trace_status: str,
        trace_message: Optional[str],
        extracted_text: Optional[str],
    ) -> None:
        """Mark session checkpoint completed or interrupted/resumable based on outcome."""
        if not self.session_id or self._is_superseded():
            return
        try:
            raw_txt = str(extracted_text or "")
            raw_low = raw_txt.lower()
            aborted = self._is_cancelled()
            timed_out = raw_txt.lstrip().startswith("⚠️ Timeout:") or ("timed out" in raw_low and raw_txt.lstrip().startswith(("⚠️", "❌")))
            loop_broken = "Loop Breaker: Stopped after" in raw_txt
            iter_limit = bool(trace_message and ("Limite iterazioni" in trace_message or "Iteration limit" in trace_message))
            is_llm_err = is_llm_error_response(raw_txt)
            if aborted or timed_out or loop_broken or iter_limit or is_llm_err or trace_status == "error" or trace_message is None:
                reason = (
                    "timeout" if timed_out
                    else (
                        "aborted" if aborted
                        else (
                            "loop_breaker" if loop_broken
                            else (
                                "iteration_limit" if iter_limit
                                else ("llm_error" if is_llm_err else "interrupted")
                            )
                        )
                    )
                )
                mark_checkpoint_status(self.session_id, "interrupted", reason=reason, final_preview=raw_txt[:200])
                try:
                    from hecos.core.action_plans import get_action_plan_manager
                    mgr = get_action_plan_manager()
                    active_plan = mgr.resolve_plan(source_id=self.session_id)
                    if active_plan and active_plan.get("status") in ("running", "paused"):
                        mgr.complete_plan(plan_id=active_plan["plan_id"], status="interrupted", summary="")
                except Exception:
                    pass
            else:
                mark_checkpoint_status(self.session_id, "completed", reason="ok", final_preview=raw_txt[:200])
                try:
                    cur_cfg = self._resolve_current_cfg()
                    if isinstance(cur_cfg, dict) and cur_cfg.get("_turn_execute_plan"):
                        from hecos.core.action_plans import get_action_plan_manager
                        mgr = get_action_plan_manager()
                        active_plan = mgr.resolve_plan(source_id=self.session_id)
                        if active_plan and active_plan.get("status") == "running":
                            steps = active_plan.get("steps") or []
                            all_done = bool(steps) and all(
                                st.get("status") in ("done", "skipped") for st in steps
                            )
                            if all_done:
                                mgr.complete_plan(
                                    plan_id=active_plan["plan_id"],
                                    status="completed",
                                    summary=raw_txt[:200] or "Plan executed in chat.",
                                    source_id=self.session_id,
                                )
                            else:
                                mgr.complete_plan(
                                    plan_id=active_plan["plan_id"],
                                    status="paused",
                                    summary="",
                                    source_id=self.session_id,
                                )
                except Exception:
                    pass
        except Exception as _ce:
            logger.debug(f"[AGENT] Checkpoint finalize skipped: {_ce}")

    def _handle_plain_text_turn(
        self,
        *,
        user_text: str,
        raw_response: Any,
        extracted_text: Optional[str],
        think_block: Optional[str],
        accumulated_tool_results: List[Dict[str, Any]],
        current_cfg: Dict[str, Any],
        iteration: int,
        retries_state: Dict[str, int],
        agent_context: List[Dict[str, Any]],
        llm_step: Dict[str, Any],
        voice_status: bool,
        missing_igen_detected: bool,
        prior_notice: Optional[str],
    ) -> Tuple[Optional[Tuple[str, str]], Optional[str]]:
        """Handle a non-tool response: trigger guard retry if hallucinated, otherwise conclude turn."""
        if is_llm_error_response(extracted_text):
            err_msg = tr("Errore nella risposta del modello", "Model response error")
            llm_step["result_preview"] = err_msg
            AgentTracer.finish_step(llm_step, status="error", result_preview=str(extracted_text or "")[:160])
            result = self._conclude_turn(
                trace_message=err_msg,
                trace_status="error",
                extracted_text=extracted_text,
                accumulated_tool_results=accumulated_tool_results,
                raw_response=raw_response,
                voice_status=voice_status,
                think_block=think_block,
                missing_igen_detected=False,
                unverified_file_notice=None,
                user_text=user_text,
            )
            return result, prior_notice

        guard_prompt, step_preview, file_notice = evaluate_plain_text_guards(
            user_text=user_text,
            raw_response=raw_response,
            extracted_text=extracted_text,
            accumulated_tool_results=accumulated_tool_results,
            current_cfg=current_cfg,
            iteration=iteration,
            max_iterations=self.max_iterations,
            retries_state=retries_state,
        )
        effective_notice = file_notice or prior_notice

        if guard_prompt:
            if step_preview:
                llm_step["result_preview"] = step_preview
                AgentTracer.update_step(llm_step, detail=step_preview)
            agent_context.append({"role": "assistant", "content": str(raw_response or extracted_text or "")})
            agent_context.append({"role": "user", "content": guard_prompt})
            return None, effective_notice

        # Plan-execution guard: if full Execute Plan is running and tools were already invoked
        # (or fake image links appeared) while pending steps remain, nudge model to finish all steps.
        if (
            isinstance(current_cfg, dict)
            and current_cfg.get("_turn_execute_plan")
            and int(current_cfg.get("_turn_single_step_index") or 0) <= 0
            and retries_state.get("plan_exec", 0) < 2
            and iteration < self.max_iterations
            and not (self.state_manager and getattr(self.state_manager, "image_gen_failed", False))
            and (
                bool(accumulated_tool_results)
                or "![" in (extracted_text or "")
                or "file:///" in (extracted_text or "").lower()
            )
        ):
            try:
                from hecos.core.action_plans import get_action_plan_manager, compute_plan_progress
                ap_mgr = get_action_plan_manager()
                act_p = ap_mgr.resolve_plan(
                    plan_id=str(current_cfg.get("_turn_execute_plan") or ""),
                    source_id=self.session_id or "",
                )
                if act_p and act_p.get("status") not in ("completed", "cancelled", "rejected"):
                    prog = compute_plan_progress(act_p)
                    rem_steps = [
                        s for s in (act_p.get("steps") or [])
                        if s.get("status") not in ("done", "skipped")
                    ]
                    if prog.get("total", 0) > 0 and rem_steps:
                        retries_state["plan_exec"] = retries_state.get("plan_exec", 0) + 1
                        nxt = rem_steps[0]
                        rem_preview = ", ".join(f"Step {s.get('index')} ({s.get('title')})" for s in rem_steps[:5])
                        logger.warning(
                            f"[AGENT] Action Plan '{act_p.get('plan_id')}' still has {len(rem_steps)} remaining step(s) — prompting continuation."
                        )
                        agent_context.append({"role": "assistant", "content": str(raw_response or extracted_text or "")})
                        agent_context.append({
                            "role": "user",
                            "content": (
                                f"[SYSTEM PLAN GUARD]: Only {prog['done']}/{prog['total']} steps of '{act_p.get('title')}' are marked done. "
                                f"Remaining unexecuted steps: {rem_preview}. "
                                f"Do NOT stop early or invent ungenerated files/links! Execute Step {nxt.get('index')} ('{nxt.get('title')}') NOW using your real tools, "
                                f"and call `ACTION_PLANS__update_step(step_index={nxt.get('index')}, status='done', notes='...')` after each finished step."
                            ),
                        })
                        return None, effective_notice
            except Exception as _pg_err:
                logger.debug(f"[AGENT] Plan continuation guard skipped: {_pg_err}")

        done_msg = tr("Risposta formulata", "Response formulated")
        llm_step["result_preview"] = done_msg

        # In Plan-Only (Architect) mode, if the model wrote a text plan without calling ACTION_PLANS__create_plan,
        # auto-extract and register the checklist so the interactive #agent-plan-slot widget always appears.
        try:
            is_plan_only = bool(
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
            called_create_plan = any(
                str(r.get("tag", "")).upper() == "ACTION_PLANS"
                and str(r.get("action") or "") in ("create_plan", "revise_plan")
                for r in accumulated_tool_results
            )
            clean_ext = (extracted_text or "").strip()
            is_llm_error_resp = clean_ext.startswith(("⚠️", "❌", "[SYSTEM"))
            if is_plan_only and not called_create_plan and clean_ext and not is_llm_error_resp:
                from hecos.core.action_plans import get_action_plan_manager
                get_action_plan_manager().ensure_fallback_plan_from_text(
                    user_text=user_text,
                    assistant_text=clean_ext,
                    source_id=self.session_id or "",
                )
        except Exception as _pe:
            logger.debug(f"[AGENT] Fallback plan extraction skipped: {_pe}")

        result = self._conclude_turn(
            trace_message=done_msg,
            trace_status="ok",
            extracted_text=extracted_text,
            accumulated_tool_results=accumulated_tool_results,
            raw_response=raw_response,
            voice_status=voice_status,
            think_block=think_block,
            missing_igen_detected=missing_igen_detected,
            unverified_file_notice=effective_notice,
            user_text=user_text,
        )
        return result, effective_notice

    def _handle_tool_calls_turn(
        self,
        *,
        user_text: str,
        raw_response: Any,
        tool_results: List[Dict[str, Any]],
        extracted_text: Optional[str],
        think_block: Optional[str],
        accumulated_tool_results: List[Dict[str, Any]],
        agent_context: List[Dict[str, Any]],
        llm_step: Dict[str, Any],
        images: Optional[List[Any]],
        iteration: int,
        voice_status: bool,
        missing_igen_detected: bool,
        stagnation_tracker: LoopStagnationTracker,
    ) -> Tuple[Optional[Tuple[str, str]], Optional[List[Any]]]:
        """Process executed tools, compact history, evaluate stagnation/termination, and conclude or continue."""
        called_tags = ", ".join(sorted({str(r.get("tag", "")) for r in tool_results if r.get("tag")}))
        if called_tags:
            llm_step["result_preview"] = tr(f"Attivazione: {called_tags}", f"Triggered: {called_tags}")

        _append_raw_assistant_context(agent_context, raw_response)
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
                video_response, clean_voice = processore.clean_final_output(
                    camera_resp, tool_results, camera_resp, voice_status
                )
                self._sync_assistant_history(video_response, user_text=user_text)
                return (video_response, clean_voice), images

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
            return None, images

        if stagnation_decision == "break":
            logger.warning(
                f"[AGENT] Repetitive loop broken early at iteration {iteration}/{self.max_iterations}: {stagnation_msg}"
            )
            brk_step = AgentTracer.start_step(
                kind="error",
                label=tr("Loop ripetitivo interrotto", "Repetitive loop aborted early"),
                icon="fa-hand",
                level="error",
                module_name="Loop Breaker",
            )
            AgentTracer.finish_step(brk_step, status="error", result_preview=stagnation_msg[:180])
            combined_text = f"{(extracted_text or '').strip()}\n\n{stagnation_msg}".strip()
            return self._conclude_turn(
                trace_message=tr("Loop ripetitivo interrotto in anticipo", "Repetitive no-progress loop broken early"),
                trace_status="error",
                extracted_text=combined_text,
                accumulated_tool_results=accumulated_tool_results,
                raw_response=raw_response,
                voice_status=voice_status,
                think_block=think_block,
                missing_igen_detected=missing_igen_detected,
                user_text=user_text,
            ), images

        should_short, reason = eval_early_termination(
            user_text=user_text,
            accumulated_tool_results=accumulated_tool_results,
            extracted_text=extracted_text,
            state_manager=self.state_manager,
            images=images,
            iteration=iteration,
        )
        if should_short:
            return self._conclude_turn(
                trace_message=reason,
                trace_status="ok",
                extracted_text=extracted_text,
                accumulated_tool_results=accumulated_tool_results,
                raw_response=raw_response,
                voice_status=voice_status,
                think_block=think_block,
                missing_igen_detected=missing_igen_detected,
                user_text=user_text,
            ), images

        if iteration == self.max_iterations:
            logger.warning(
                f"[AGENT] Maximum thought iterations ({self.max_iterations}) reached — returning best available response."
            )
            return self._conclude_turn(
                trace_message=tr("Limite iterazioni raggiunto — invio risposta", "Iteration limit reached — returning response"),
                trace_status="ok",
                extracted_text=extracted_text,
                accumulated_tool_results=accumulated_tool_results,
                raw_response=raw_response,
                voice_status=voice_status,
                think_block=think_block,
                missing_igen_detected=missing_igen_detected,
                user_text=user_text,
            ), images

        return None, images

    def run_agentic_loop(
        self,
        user_text: str,
        voice_status: bool = False,
        images: Optional[List[Any]] = None,
        resume_checkpoint: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, str]:
        """
        Runs the full autonomous loop:
        1. Checks global direct commands.
        2. Sets up image limits and checks for missing packages.
        3. Iterates: LLM inference -> Tool extraction & execution -> Termination checks.
        """
        try:
            return self._run_agentic_loop_impl(
                user_text=user_text,
                voice_status=voice_status,
                images=images,
                resume_checkpoint=resume_checkpoint,
            )
        finally:
            try:
                AgentTracer.unbind()
            except Exception:
                pass

    def _run_agentic_loop_impl(
        self,
        user_text: str,
        voice_status: bool = False,
        images: Optional[List[Any]] = None,
        resume_checkpoint: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, str]:
        sess = AgentTracer.bind(
            state_manager=self.state_manager,
            trace_callback=self.trace_callback,
            session_id=self.session_id,
            turn_id=self.turn_id,
            cancel_event=self.cancel_event,
        )
        try:
            init_cfg = self._resolve_current_cfg()
            if sess is not None and isinstance(getattr(sess, "config", None), dict) and isinstance(init_cfg, dict):
                if init_cfg.get("_turn_plan_only"):
                    sess.config["_turn_plan_only"] = True
                if init_cfg.get("_turn_revise_plan_id"):
                    sess.config["_turn_revise_plan_id"] = str(init_cfg["_turn_revise_plan_id"])
        except Exception:
            pass

        intercepted, response_output = CommandInterceptor.intercept(user_text, self)
        if intercepted:
            self._finalize_and_store_trace(tr("Comando diretto completato", "Direct command completed"))
            return processore.clean_final_output(response_output, [], response_output, voice_status)
        if response_output:
            user_text = response_output

        if not self.is_enabled:
            logger.info("[AGENT] Agentic Loop is disabled in config. Running single iteration.")
            self.max_iterations = 1

        boot_cfg = self._resolve_current_cfg()
        _exec_plan_id = str(boot_cfg.get("_turn_execute_plan") or "").strip() if isinstance(boot_cfg, dict) else ""
        try:
            _single_step_idx = int(boot_cfg.get("_turn_single_step_index") or 0) if isinstance(boot_cfg, dict) else 0
        except (TypeError, ValueError):
            _single_step_idx = 0
        _exec_plan = None
        if _exec_plan_id:
            try:
                from hecos.core.action_plans import get_action_plan_manager
                _exec_plan = get_action_plan_manager().resolve_plan(
                    plan_id=_exec_plan_id,
                    source_id=self.session_id or "",
                )
            except Exception:
                _exec_plan = None

        try:
            from hecos.core.processing.tool_dispatcher import get_requested_image_limit
            if self.state_manager:
                self.state_manager.requested_image_limit = get_requested_image_limit(
                    user_text,
                    active_plan=_exec_plan,
                    single_step_index=_single_step_idx,
                )
                self.state_manager.total_images_in_turn = 0
                self.state_manager.image_gen_failed = False
                self.state_manager.active_execute_plan_id = str((_exec_plan or {}).get("plan_id") or _exec_plan_id or "")
                self.state_manager.active_execute_single_step = _single_step_idx
        except Exception as _e:
            logger.debug(f"[AGENT] Failed to set image limit: {_e}")

        missing_igen_detected = is_uninstalled_image_gen_request(user_text)
        if missing_igen_detected:
            emit_missing_image_gen_warning()

        iteration = 0
        retries_state: Dict[str, int] = {"stream": 0, "file": 0, "netsearch": 0}
        unverified_file_notice: Optional[str] = None
        stagnation_tracker = LoopStagnationTracker()
        agent_context: List[Dict[str, Any]] = []
        accumulated_tool_results: List[Dict[str, Any]] = []
        emitted_mode_badge = False

        if isinstance(resume_checkpoint, dict):
            resumed = build_resume_state(resume_checkpoint, default_max_iterations=self.max_iterations)
            user_text = resumed["user_text"] or user_text
            iteration = resumed["start_iteration"]
            self.max_iterations = resumed["max_iterations"]
            agent_context = resumed["agent_context"]
            accumulated_tool_results = resumed["accumulated_tool_results"]
            retries_state = resumed["retries_state"]
            logger.info(f"[AGENT] Resuming session from checkpoint at step {iteration}/{self.max_iterations}")

        boot_cfg = self._resolve_current_cfg()
        if not self._explicit_max_iterations:
            if _is_coding_loop_active(boot_cfg):
                self.max_iterations = max(self.max_iterations, 25)
            if _exec_plan_id and _single_step_idx == 0:
                step_count = len((_exec_plan or {}).get("steps") or [])
                self.max_iterations = max(self.max_iterations, min(45, max(25, step_count * 2 + 6)))

        self._persist_checkpoint(
            user_text=user_text,
            iteration=iteration,
            agent_context=agent_context,
            accumulated_tool_results=accumulated_tool_results,
            retries_state=retries_state,
            current_cfg=boot_cfg,
            status="running",
            reason="resumed" if resume_checkpoint else "started",
        )

        with LoopWatchdog(self.trace_callback):
            while iteration < self.max_iterations:
                if self._is_cancelled():
                    if not self._is_superseded():
                        self._finalize_and_store_trace(
                            tr("Operazione interrotta dall'utente", "Operation aborted by user"),
                            status="error",
                        )
                    break

                iteration += 1
                logger.info(f"[AGENT] --- Iteration {iteration}/{self.max_iterations} ---")
                current_cfg = self._resolve_current_cfg()

                if not emitted_mode_badge:
                    emitted_mode_badge = True
                    self._emit_mode_step(current_cfg)
                    if images and iteration == 1:
                        user_text, images = process_initial_vision(
                            user_text, images, current_cfg, emit_callback=self._emit
                        )

                enforce_agent_context_budget(agent_context, current_cfg, user_text=user_text)

                llm_label = (
                    tr("Elaborazione richiesta", "Analyzing request & generating response")
                    if iteration == 1
                    else tr(f"Sintesi risultati ed elaborazione (Step {iteration})", f"Synthesizing tool results (Step {iteration})")
                )
                llm_step = AgentTracer.start_step(
                    kind="llm",
                    label=llm_label,
                    detail=resolve_short_model_label(current_cfg),
                    icon="fa-brain",
                    level="info",
                    module_name="AI Brain",
                )
                try:
                    raw_response = brain.generate_response(
                        user_text,
                        external_config=current_cfg,
                        agent_context=agent_context,
                        save_history=False,
                        images=images,
                        user_id=self.current_user_id,
                        session_id=self.session_id,
                        sender_tab_id=self.sender_tab_id,
                    )
                except Exception as llm_exc:
                    AgentTracer.finish_step(llm_step, status="error", result_preview=str(llm_exc))
                    raise

                AgentTracer.finish_step(llm_step, status="ok")

                if self._is_cancelled():
                    logger.info(f"[AGENT] Turn '{self.turn_id or 'legacy'}' aborted immediately after LLM return.")
                    if not self._is_superseded():
                        self._finalize_and_store_trace(
                            tr("Operazione interrotta dall'utente", "Operation aborted by user"),
                            status="error",
                        )
                    break

                tools_called, tool_results, extracted_text, think_block = processore.extract_and_execute_tools(
                    raw_response, self.config, sm=self.state_manager
                )
                if self._is_cancelled():
                    logger.info(f"[AGENT] Turn '{self.turn_id or 'legacy'}' aborted during/after tool dispatch.")
                    break
                if think_block:
                    self._emit({"type": "think", "text": think_block}, level="think")
                self._sync_telemetry()

                if not tools_called:
                    result, unverified_file_notice = self._handle_plain_text_turn(
                        user_text=user_text,
                        raw_response=raw_response,
                        extracted_text=extracted_text,
                        think_block=think_block,
                        accumulated_tool_results=accumulated_tool_results,
                        current_cfg=current_cfg,
                        iteration=iteration,
                        retries_state=retries_state,
                        agent_context=agent_context,
                        llm_step=llm_step,
                        voice_status=voice_status,
                        missing_igen_detected=missing_igen_detected,
                        prior_notice=unverified_file_notice,
                    )
                    if result is not None:
                        return result
                    self._persist_checkpoint(
                        user_text=user_text,
                        iteration=iteration,
                        agent_context=agent_context,
                        accumulated_tool_results=accumulated_tool_results,
                        retries_state=retries_state,
                        current_cfg=current_cfg,
                    )
                    continue

                result, images = self._handle_tool_calls_turn(
                    user_text=user_text,
                    raw_response=raw_response,
                    tool_results=tool_results,
                    extracted_text=extracted_text,
                    think_block=think_block,
                    accumulated_tool_results=accumulated_tool_results,
                    agent_context=agent_context,
                    llm_step=llm_step,
                    images=images,
                    iteration=iteration,
                    voice_status=voice_status,
                    missing_igen_detected=missing_igen_detected,
                    stagnation_tracker=stagnation_tracker,
                )
                if result is not None:
                    return result
                self._persist_checkpoint(
                    user_text=user_text,
                    iteration=iteration,
                    agent_context=agent_context,
                    accumulated_tool_results=accumulated_tool_results,
                    retries_state=retries_state,
                    current_cfg=current_cfg,
                )

        if self._is_superseded():
            logger.info(f"[AGENT] Superseded turn '{self.turn_id or ''}' exiting silently without mutating history/plan.")
            return "", ""

        if self._is_cancelled():
            self._finalize_checkpoint(
                trace_status="error",
                trace_message=tr("Operazione interrotta dall'utente", "Operation aborted by user"),
                extracted_text="⛔ Generation aborted.",
            )
            return "⛔ Generation aborted.", ""

        return self._conclude_turn(
            trace_message=None,
            extracted_text=None,
            accumulated_tool_results=accumulated_tool_results,
            raw_response="",
            voice_status=voice_status,
            user_text=user_text,
        )
