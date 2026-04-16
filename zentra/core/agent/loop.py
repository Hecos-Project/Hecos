import os
import time
import json
from zentra.core.logging import logger
from zentra.core.llm import brain
from zentra.core.agent.traces import AgentTracer
from zentra.core.processing import processore
from zentra.core.i18n import translator

class AgentExecutor:
    """
    Zentra Phase 2 - Agentic Loop
    Orchestrates the repeated multi-turn connection between Brain and Plugins.
    """
    
    def __init__(self, config=None, config_manager=None, state_manager=None, max_iterations=None, trace_callback=None, current_user_id="admin"):
        self.config = config
        self.config_manager = config_manager
        self.state_manager = state_manager
        self.current_user_id = current_user_id
        # Optional direct callback for WebUI session traces.
        # Signature: trace_callback(msg: str, level: str) -> None
        self.trace_callback = trace_callback
        
        # Load dedicated agent configuration
        self.agent_config = {"enabled": True, "max_iterations": 5, "verbose_traces": True}
        try:
            from zentra.config.yaml_utils import load_yaml
            from zentra.config.schemas.agent_schema import AgentConfig
            _agent_cfg_path = os.path.normpath(
                os.path.join(os.path.dirname(__file__), "..", "..", "config", "data", "agent.yaml")
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
        
        # --- GLOBAL DIRECT COMMANDS INTERCEPTOR (BYPASS LLM) ---
        testo_pulito = user_text.strip()
        if testo_pulito.lower().startswith(("/img ", "/image ", "/photo ", "/foto ")):
            try:
                raw_prompt = testo_pulito.split(" ", 1)[1].strip()
                self._emit(f"Direct Command Intercepted: {testo_pulito[:10]}...", level="info")
                
                # Semantic Cleaning: Remove "a photo of", "a picture of", etc. to avoid redundancy
                clean_target = raw_prompt.lower()
                for unwanted in ["a photo of ", "a picture of ", "una foto di ", "un'immagine di ", "photo of ", "picture of "]:
                    clean_target = clean_target.replace(unwanted, "")
                
                # Smart Enrichment: If user says 'you/me/persona_name', add persona visual context
                active_p = self.config.get('ai', {}).get('active_personality', 'Zentra_System_Soul.yaml')
                persona_name_raw = active_p.replace('.yaml', '').replace('_', ' ').lower()
                persona_short = persona_name_raw.split(' ')[0] # e.g. "urania"
                
                enrich_keywords = ["you", "me", "tua", "mia", "tuo", "tuoi", "yourself", "te ", persona_short, persona_name_raw]
                prompt_bypass = clean_target
                
                if any(k in raw_prompt.lower() for k in enrich_keywords):
                    visual_desc = self._get_persona_visual_description()
                    if visual_desc:
                        self._emit(f"Enriching prompt with persona YAML context: {persona_short}...", level="info")
                        # Construct a clean, professional prompt for the provider
                        target_action = clean_target.replace('you', '').replace('your', '').replace('tua', '').replace('me', '').replace(persona_short, '').strip()
                        # Clean up punctuation after removal
                        target_action = target_action.lstrip(',').lstrip('.').strip()
                        prompt_bypass = f"A photo of {visual_desc}, {target_action}" if target_action else f"A photo of {visual_desc}"
                
                from zentra.plugins.image_gen.main import tools as image_gen_tools
                result = image_gen_tools.generate_image(prompt_bypass)
                
                # Save to memory to keep the context consistent
                from zentra.memory import brain_interface
                brain_interface.save_message("user", testo_pulito, config=self.config_manager.config if self.config_manager else self.config, user_id=self.current_user_id)
                brain_interface.save_message("assistant", result, config=self.config_manager.config if self.config_manager else self.config, user_id=self.current_user_id)
                
                # Format for output (video/voice)
                return processore.clean_final_output(result, [], result, voice_status)
            except Exception as e:
                logger.error(f"[AGENT] Direct Bypass Error: {e}")
                err_msg = f"❌ Error: {e}"
                return processore.clean_final_output(err_msg, [], err_msg, voice_status)
        # -------------------------------------------------------

        if not self.is_enabled:
            logger.info("[AGENT] Agentic Loop is disabled in config. Running single iteration.")
            self.max_iterations = 1
            
        iteration = 0
        # agent_context accumulates assistant and tool messages for the current chat session
        agent_context = []
        # Accumulate ALL tool results across iterations so the final response can reference them
        accumulated_tool_results = []
        
        while iteration < self.max_iterations:
            iteration += 1
            logger.info(f"[AGENT] --- Iteration {iteration}/{self.max_iterations} ---")
            
            # The first call must save the initial user prompt. Subsequent loops do not.
            save_hist = (iteration == 1)
            
            # 1. Call the Brain
            # Ensure we use the latest config from the manager if available
            current_cfg = self.config_manager.config if self.config_manager else self.config
            
            self._emit(f"Thinking (Loop {iteration})...", level="info")
            raw_response = brain.generate_response(
                user_text, 
                external_config=current_cfg, 
                agent_context=agent_context,
                save_history=save_hist,
                images=images,
                user_id=self.current_user_id,
                session_id=None # brain can get it from privacy_manager if None
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
                
                # Check for explicit safety blocks from client.py
                if "!!!BLOCK_SAFETY!!!" in str(extracted_text):
                    if translator.get_translator().language == 'it':
                        extracted_text = "Spiacente, questa richiesta è stata bloccata dai filtri di sicurezza del provider AI (Content Filter). Prova a riformulare con termini meno sensibili."
                    else:
                        extracted_text = "I'm sorry, but this request was blocked by the AI provider's safety filters (Content Filter). Please try rephrasing with less sensitive terms."

                # ── Server Image Rendering ──────────────────────────────────────────
                # If any tool returned an image path (e.g. WEBCAM target='server'),
                # append it as a markdown image so the user can actually see it.
                # We use the new /snapshots/ route for this.
                import re
                for res in tool_results:
                    out = res.get("output", "")
                    if out and isinstance(out, str):
                        # 1. Check for explicit [[IMG:...]] from ImageGen
                        img_tags = re.findall(r'\[\[IMG:([^\]]+)\]\]', out)
                        for idx, tag in enumerate(img_tags):
                            # Append directly as expected by chat UI
                            if f"[[IMG:{tag}]]" not in extracted_text:
                                extracted_text += f"\n\n[[IMG:{tag}]]"
                                
                        # 2. Check for raw paths (e.g. from WEBCAM module which saves to /snapshots)
                        potential_paths = re.findall(r'([\w\.\-\\/]+\.(?:jpg|jpeg|png))', out, re.IGNORECASE)
                        for path in potential_paths:
                            fname = os.path.basename(path)
                            if fname in img_tags:
                                continue  # Covered above
                            
                            # Convert local path to web URL for WEBCAM
                            img_url = f"/snapshots/{fname}"
                            if img_url not in extracted_text:
                                extracted_text += f"\n\n![Snapshot]({img_url})"
                # ────────────────────────────────────────────────────────────────────

                # IMPORTANT: If it took loops, we must save the FINAL response to history manually.
                if iteration > 1:
                    from zentra.memory import brain_interface
                    brain_interface.save_message("assistant", extracted_text, config=self.config, user_id=self.current_user_id)
                
                # Proceed to voice/video cleaning
                # DEBUG: log what we pass to clean_final_output
                try:
                    import datetime
                    _img_p = r'\[\[IMG:'
                    _has_i = bool(re.search(_img_p, extracted_text))
                    _zentra_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
                    _log_path = os.path.join(_zentra_dir, "logs", "image_gen_debug.txt")
                    os.makedirs(os.path.dirname(_log_path), exist_ok=True)
                    with open(_log_path, "a", encoding="utf-8") as _dbg:
                        _now = datetime.datetime.now().strftime("%H:%M:%S")
                        _dbg.write(f"[{_now}] [LoopDebug] tool_results count={len(tool_results)}, extracted_text_has_img={_has_i}\n")
                        _dbg.write(f"[{_now}] [LoopDebug] extracted_text={extracted_text[:300]}\n")
                        for ri, rr in enumerate(tool_results):
                            _out = str(rr.get('output', ''))[:200]
                            _dbg.write(f"[{_now}] [LoopDebug] tool_result[{ri}] tag={rr.get('tag')} output={_out}\n")
                except Exception:
                    pass
                video_response, clean_voice = processore.clean_final_output(extracted_text, accumulated_tool_results, raw_response, voice_status)
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
                # Also accumulate for final response rendering (e.g. [[IMG:...]] tags)
                accumulated_tool_results.extend(tool_results)
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

    def _get_persona_visual_description(self):
        """Attempts to extract a visual description of the current AI identity from YAML or fallback."""
        try:
            # 1. Identity the active personality file
            # Robust dict access for the plain dict 'self.config'
            active_p = self.config.get('ai', {}).get('active_personality', 'Zentra_System_Soul.yaml')
            
            # 2. Try to load the YAML file
            from zentra.config.yaml_utils import load_yaml
            # root_dir from zentra/core/agent/loop.py:
            # os.path.dirname(__file__) -> zentra/core/agent
            # .. -> zentra/core
            # .. -> zentra
            root_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
            p_path = os.path.join(root_dir, "personality", active_p)
            
            # If still not found, try one level up (workspace root) just in case
            if not os.path.exists(p_path):
                p_path = os.path.join(root_dir, "..", "zentra", "personality", active_p)
            
            if os.path.exists(p_path):
                import yaml
                with open(p_path, 'r', encoding='utf-8') as f:
                    p_data = yaml.safe_load(f)
                
                # Check for the new dynamic field
                v_desc = p_data.get("visual_description")
                if v_desc:
                    return v_desc

            # 3. Hard-coded fallback for legacy or missing fields
            name = active_p.lower()
            if "urania" in name:
                return "a beautiful female cybernetic android with bright turquoise neon-blue hair, bright blue eyes, wearing white and pink-glowing circuitry armor"
            elif "motoko" in name:
                return "Major Motoko Kusanagi from Ghost in the Shell, purple hair, tactical suit"
            elif "atlas" in name:
                return "a handsome, professional and futuristic man with a sharp jawline"
            
            # Generic fallbacks
            if "woman" in name or "femmina" in name:
                return "a beautiful woman"
            elif "man" in name or "maschio" in name:
                return "a handsome man"
                
            return "a futuristic person"
        except Exception as e:
            logger.debug(f"[AGENT] Failed to load dynamic visual description: {e}")
            return "a digital entity"
