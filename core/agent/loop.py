import os
import time
from core.logging import logger
from core.llm import brain
from core.agent.traces import AgentTracer
from core.processing import processore
from core.i18n import translator

class AgentExecutor:
    """
    Zentra Phase 2 - Agentic Loop
    Orchestrates the repeated multi-turn connection between Brain and Plugins.
    """
    
    def __init__(self, config=None, state_manager=None, max_iterations=None, trace_callback=None):
        self.config = config
        self.state_manager = state_manager
        # Optional direct callback for WebUI session traces.
        # Signature: trace_callback(msg: str, level: str) -> None
        self.trace_callback = trace_callback
        
        # Load dedicated agent configuration
        self.agent_config = {"enabled": True, "max_iterations": 5, "verbose_traces": True}
        try:
            from config.yaml_utils import load_yaml
            from config.schemas.agent_schema import AgentConfig
            _agent_cfg_path = os.path.normpath(
                os.path.join(os.path.dirname(__file__), "..", "..", "config", "agent.yaml")
            )
            agent_model = load_yaml(_agent_cfg_path, AgentConfig)
            self.agent_config = agent_model.model_dump()
        except Exception as e:
            logger.error(f"[AGENT] Error loading agent.yaml: {e}")

        self.max_iterations = max_iterations if max_iterations is not None else self.agent_config.get("max_iterations", 5)
        self.is_enabled = self.agent_config.get("enabled", True)
        
    def _emit(self, msg: str, level: str = "info"):
        """Routes a trace to both the terminal tracer and the optional session callback."""
        # If trace_callback is present, we are in a /api/stream session.
        # Sending it to state_manager too would duplicate the trace via /api/events.
        sm_for_trace = self.state_manager if not self.trace_callback else None
        AgentTracer.emit(sm_for_trace, msg, level=level)
        
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
        # Privacy-oriented log: avoid echoing private user text on the server physical console.
        self._emit(f"Analyzing incoming user request...", level="info")
        if not self.is_enabled:
            logger.info("[AGENT] Agentic Loop is disabled in config. Running single iteration.")
            self.max_iterations = 1
            
        iteration = 0
        # agent_context accumulates assistant and tool messages for the current chat session
        agent_context = []  
        
        while iteration < self.max_iterations:
            iteration += 1
            logger.info(f"[AGENT] --- Iteration {iteration}/{self.max_iterations} ---")
            
            # The first call must save the initial user prompt. Subsequent loops do not.
            save_hist = (iteration == 1)
            
            # 1. Call the Brain
            self._emit(f"Thinking (Loop {iteration})...", level="info")
            raw_response = brain.generate_response(
                user_text, 
                external_config=self.config, 
                agent_context=agent_context,
                save_history=save_hist,
                images=images
            )
            
            # 2. Extract tools using the processor utility
            tools_called, tool_results, extracted_text = processore.extract_and_execute_tools(raw_response, self.config)
            
            if not tools_called:
                # BREAK CONDITION: The LLM didn't call any tools, so it produced the final response.
                self._emit("Response formulated.", level="success")
                
                # If the AI produces NO text (common for some models after tool calls),
                # provide a friendly fallback instead of showing an error.
                if not extracted_text or not extracted_text.strip():
                    if tool_results:
                        extracted_text = f"I have executed the requested actions: {', '.join([r.get('tag') for r in tool_results])}."
                    else:
                        extracted_text = "I'm thinking, but I don't have a specific text response yet. How can I help further?"

                # ── Server Image Rendering ──────────────────────────────────────────
                # If any tool returned an image path (e.g. WEBCAM target='server'),
                # append it as a markdown image so the user can actually see it.
                # We use the new /snapshots/ route for this.
                import re
                for res in tool_results:
                    out = res.get("output", "")
                    if out and isinstance(out, str):
                        potential_paths = re.findall(r'([\w\.\-\\/]+\.(?:jpg|jpeg|png))', out, re.IGNORECASE)
                        for path in potential_paths:
                            fname = os.path.basename(path)
                            # Convert local path to web URL
                            img_url = f"/snapshots/{fname}"
                            extracted_text += f"\n\n![Snapshot]({img_url})"
                # ────────────────────────────────────────────────────────────────────

                # IMPORTANT: If it took loops, we must save the FINAL response to history manually.
                if iteration > 1:
                     from memory import brain_interface
                     brain_interface.save_message("assistant", extracted_text, config=self.config)
                
                # Proceed to voice/video cleaning
                video_response, clean_voice = processore.clean_final_output(extracted_text, tool_results, raw_response, voice_status)
                return video_response, clean_voice
                
            else:
                # LOOP CONDITION: The LLM used a tool.
                
                # A) Add the assistant's tool call to context (required by many APIs for chaining)
                # raw_response is expected to be a LiteLLM Message object here if tools_called is True
                if hasattr(raw_response, 'role'):
                    # Convert LiteLLM/OpenAI object to serializable dict
                    if hasattr(raw_response, 'model_dump'):
                        agent_context.append(raw_response.model_dump())
                    elif hasattr(raw_response, 'dict'):
                        agent_context.append(raw_response.dict())
                    else:
                        agent_context.append(json.loads(json.dumps(raw_response, default=lambda o: o.__dict__)))
                else:
                    # Fallback for non-object responses (tags)
                    agent_context.append({"role": "assistant", "content": str(raw_response)})

                # B) Execute tool and add 'tool' results to context
                for res in tool_results:
                    self._emit(f"Tool execution result: {res.get('tag')}", level="tool")
                    
                    output_text = res.get("output")
                    
                    # ── Client Camera Short-Circuit ───────────────────────────────────────
                    # When WEBCAM is called with target='client', it returns a signal 
                    # asking the AI to output [CAMERA_SNAPSHOT_REQUEST]. Instead of relying
                    # on the LLM to do this (it gets confused), we intercept it here and
                    # construct the final response directly — guaranteeing the token reaches
                    # the Javascript interceptor in the browser.
                    CAMERA_TOKEN = "[CAMERA_SNAPSHOT_REQUEST]"
                    if output_text and CAMERA_TOKEN in str(output_text).strip():
                        self._emit("Client camera request intercepted — forwarding directly to browser.", level="info")
                        # Use the user's personality or a polite default
                        final_response = f"Sure! {CAMERA_TOKEN} Please take the photo when prompted by your browser."
                        video_response, clean_voice = processore.clean_final_output(final_response, tool_results, final_response, voice_status)
                        return video_response, clean_voice
                    
                    if res.get("tag") == "WEBCAM":
                        logger.debug(f"[AGENT] WEBCAM result did NOT trigger short-circuit. Output: '{str(output_text)[:50]}...'")
                    # ─────────────────────────────────────────────────────────────────────
                    
                    # Native Tool Message
                    agent_context.append({
                        "role": "tool",
                        "tool_call_id": res.get("id"),
                        "name": res.get("tag"),
                        "content": output_text
                    })
                    
                    # Intercept Image Paths for Vision-AI
                    if output_text and isinstance(output_text, str):
                        import re
                        import mimetypes
                        import base64
                        # Identify file paths ending with typical image extensions
                        potential_paths = re.findall(r'([\w\.\-\\/]+\.(?:jpg|jpeg|png))', output_text, re.IGNORECASE)
                        for path in potential_paths:
                            if os.path.exists(path):
                                try:
                                    with open(path, "rb") as f:
                                        img_bytes = f.read()
                                    if images is None:
                                        images = []
                                    mime, _ = mimetypes.guess_type(path)
                                    # Pre-encode as base64 to avoid double-encoding in adapters
                                    images.append({
                                        "data_b64": base64.b64encode(img_bytes).decode("utf-8"),
                                        "mime_type": mime or "image/jpeg",
                                        "name": os.path.basename(path)
                                    })
                                    self._emit(f"Intercepted image for Vision-AI: {os.path.basename(path)}", level="info")
                                    logger.info(f"[AGENT] Vision-AI: loaded {os.path.basename(path)} ({len(img_bytes)} bytes)")
                                except Exception as e:
                                    logger.debug(f"[AGENT] Failed to load intercepted image path {path}: {e}")
                    
                self._emit("Analyzing tool results...", level="info")
                
                if iteration == self.max_iterations:
                    self._emit("Maximum thought limit reached.", level="error")
                    video_response, clean_voice = processore.clean_final_output("I have reached the processing limit. " + extracted_text, tool_results, raw_response, voice_status)
                    return video_response, clean_voice
