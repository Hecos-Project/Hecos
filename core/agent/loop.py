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
        config_path = os.path.join(os.path.dirname(__file__), "config_agent.json")
        try:
            if os.path.exists(config_path):
                import json
                with open(config_path, "r", encoding="utf-8") as f:
                    file_conf = json.load(f)
                    self.agent_config.update(file_conf)
        except Exception as e:
            logger.error(f"[AGENT] Error loading config_agent.json: {e}")
            
        self.max_iterations = max_iterations if max_iterations is not None else self.agent_config.get("max_iterations", 5)
        self.is_enabled = self.agent_config.get("enabled", True)
        
    def _emit(self, msg: str, level: str = "info"):
        """Routes a trace to both the terminal tracer and the optional session callback."""
        AgentTracer.emit(self.state_manager, msg, level=level)
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
        self._emit(f"Analyzing request: '{user_text[:30]}...'", level="info")
        
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
                    
                    # Native Tool Message
                    agent_context.append({
                        "role": "tool",
                        "tool_call_id": res.get("id"),
                        "name": res.get("tag"),
                        "content": res.get("output")
                    })
                    
                self._emit("Analyzing tool results...", level="info")
                
                if iteration == self.max_iterations:
                    self._emit("Maximum thought limit reached.", level="error")
                    video_response, clean_voice = processore.clean_final_output("I have reached the processing limit. " + extracted_text, tool_results, raw_response, voice_status)
                    return video_response, clean_voice
