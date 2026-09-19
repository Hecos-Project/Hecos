import os
import json
import re
from hecos.core.logging import logger
from hecos.core.llm import brain
from hecos.core.agent.traces import AgentTracer
from hecos.core.processing import processore
from hecos.core.i18n import translator

# --- NEW HELPERS ---
from hecos.core.agent.direct_commands import CommandInterceptor
from hecos.core.agent.media_interceptor import MediaInterceptor

class AgentExecutor:
    """
    Hecos Phase 2 - Agentic Loop
    Orchestrates the repeated multi-turn connection between Brain and Plugins.
    """
    
    def __init__(self, config=None, config_manager=None, state_manager=None, max_iterations=None, trace_callback=None, current_user_id="admin", current_user_role="admin", session_id=None, sender_tab_id=None):
        self.config = config
        self.config_manager = config_manager
        self.state_manager = state_manager
        self.current_user_id = current_user_id
        self.current_user_role = current_user_role
        self.session_id = session_id
        self.sender_tab_id = sender_tab_id
        # Optional direct callback for WebUI session traces.
        self.trace_callback = trace_callback
        
        # Load dedicated agent configuration
        self.agent_config = {"enabled": True, "max_iterations": 5, "verbose_traces": True}
        try:
            from hecos.config.yaml_utils import load_yaml
            from hecos.config.schemas.agent_schema import AgentConfig
            _agent_cfg_path = os.path.normpath(
                os.path.join(os.path.dirname(__file__), "..", "..", "config", "data", "agent.yaml")
            )
            agent_model = load_yaml(_agent_cfg_path, AgentConfig)
            self.agent_config = agent_model.model_dump()
        except Exception as e:
            logger.error(f"[AGENT] Error loading agent.yaml: {e}")

        self.max_iterations = max_iterations if max_iterations is not None else self.agent_config.get("max_iterations", 5)
        self.is_enabled = self.agent_config.get("enabled", True)
        
    def _emit(self, msg, level: str = "info"):
        """Routes a trace to both the terminal tracer and the optional session callback."""
        sm_for_trace = self.state_manager if not self.trace_callback else None
        AgentTracer.emit(sm_for_trace, msg if isinstance(msg, str) else str(msg), level=level)
        
        if self.trace_callback:
            try:
                self.trace_callback(msg, level)
            except Exception as e:
                logger.debug(f"[AGENT] trace_callback error: {e}")

    def run_agentic_loop(self, user_text, voice_status=False, images=None):
        """
        Runs the full autonomous loop. 
        Calls the LLM, checks if tools are requested, executes them, feeds the result back.
        Repeats until the LLM returns plain text without tools or hits max iterations.
        """
        self._emit(f"Analyzing incoming user request...", level="info")
        AgentTracer.bind(self.state_manager)
        
        # --- GLOBAL DIRECT COMMANDS INTERCEPTOR ---
        intercepted, response_output = CommandInterceptor.intercept(user_text, self)
        if intercepted:
            return processore.clean_final_output(response_output, [], response_output, voice_status)
        # ------------------------------------------

        if not self.is_enabled:
            logger.info("[AGENT] Agentic Loop is disabled in config. Running single iteration.")
            self.max_iterations = 1
            
        iteration = 0
        agent_context = []
        accumulated_tool_results = []
        
        while iteration < self.max_iterations:
            if self.state_manager and getattr(self.state_manager, "webui_stop_requested", False):
                self._emit("Operation aborted by user.", level="error")
                break
                
            iteration += 1
            logger.info(f"[AGENT] --- Iteration {iteration}/{self.max_iterations} ---")
            
            save_hist = (iteration == 1)
            current_cfg = self.config_manager.config if getattr(self, 'config_manager', None) else processore.current_config
            
            self._emit(f"Working (Step {iteration})...", level="info")
            raw_response = brain.generate_response(
                user_text, 
                external_config=current_cfg, 
                agent_context=agent_context,
                save_history=save_hist,
                images=images,
                user_id=self.current_user_id,
                session_id=self.session_id,
                sender_tab_id=self.sender_tab_id
            )
            
            if self.state_manager and getattr(self.state_manager, "webui_stop_requested", False):
                self._emit("Operation aborted by user.", level="error")
                break
            
            tools_called, tool_results, extracted_text, think_block = processore.extract_and_execute_tools(raw_response, self.config, sm=self.state_manager)
            
            if think_block:
                self._emit({"type": "think", "text": think_block}, level="think")
            
            # Telemetry sync
            if self.state_manager:
                try:
                    from hecos.core.llm.client import LAST_PAYLOAD_INFO
                    self.state_manager.last_model = LAST_PAYLOAD_INFO.get("model")
                    self.state_manager.last_tokens_prompt = LAST_PAYLOAD_INFO.get("prompt_tokens", 0)
                    self.state_manager.last_tokens_completion = LAST_PAYLOAD_INFO.get("completion_tokens", 0)
                except Exception as e:
                    logger.debug(f"[AGENT] Telemetry sync error: {e}")
            
            if not tools_called:
                self._emit("Response formulated.", level="success")
                
                if not extracted_text or not extracted_text.strip():
                    if tool_results:
                        extracted_text = f"I have executed the requested actions: {', '.join([r.get('tag') for r in tool_results])}."
                    elif think_block:
                        extracted_text = "I've analyzed your request but couldn't formulate a final response. Please try rephrasing or using a different model."
                    else:
                        extracted_text = "I'm thinking, but I don't have a specific text response yet. How can I help further?"
                
                if "!!!BLOCK_SAFETY!!!" in str(extracted_text):
                    if translator.get_translator().language == 'it':
                        extracted_text = "Spiacente, questa richiesta è stata bloccata dai filtri di sicurezza del provider AI (Content Filter). Prova a riformulare con termini meno sensibili."
                    else:
                        extracted_text = "I'm sorry, but this request was blocked by the AI provider's safety filters (Content Filter). Please try rephrasing with less sensitive terms."

                if think_block:
                    extracted_text = f"<think>\n{think_block}\n</think>\n\n{extracted_text}"

                # Append UI images and rich media using the helper
                extracted_text = MediaInterceptor.append_ui_media_to_text(extracted_text, accumulated_tool_results)

                if iteration > 1:
                    from hecos.memory import brain_interface
                    _clean_for_hist = re.sub(r'<think>[\s\S]*?</think>\s*', '', extracted_text, flags=re.IGNORECASE).strip()
                    if '</think>' in _clean_for_hist:
                        _clean_for_hist = _clean_for_hist.split('</think>', 1)[-1].strip()
                    brain_interface.save_message("assistant", _clean_for_hist, config=self.config, user_id=self.current_user_id, session_id=self.session_id, sender_tab_id=self.sender_tab_id)
                
                video_response, clean_voice = processore.clean_final_output(extracted_text, accumulated_tool_results, raw_response, voice_status)
                return video_response, clean_voice
                
            else:
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
                        
                    self._emit(f"Tool execution result: {res.get('tag')}", level="tool")
                    output_text = res.get("output")
                    
                    if MediaInterceptor.check_webcam_short_circuit(output_text):
                        self._emit("Client camera request intercepted — forwarding directly to browser.", level="info")
                        final_response = f"Sure! [CAMERA_SNAPSHOT_REQUEST] Please take the photo when prompted by your browser."
                        video_response, clean_voice = processore.clean_final_output(final_response, tool_results, final_response, voice_status)
                        return video_response, clean_voice
                    
                    agent_context.append({
                        "role": "tool",
                        "tool_call_id": res.get("id"),
                        "name": res.get("tag"),
                        "content": output_text
                    })
                    
                    images = MediaInterceptor.load_vision_images(output_text, images, self._emit)
                    
                self._emit("Analyzing tool results...", level="info")
                
                if iteration == self.max_iterations:
                    logger.warning(f"[AGENT] Maximum thought iterations ({self.max_iterations}) reached — returning best available response.")
                    self._emit("Thought limit reached — returning response.", level="info")
                    video_response, clean_voice = processore.clean_final_output(extracted_text, tool_results, raw_response, voice_status)
                    return video_response, clean_voice
