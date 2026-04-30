import os
import json
import logging
from hecos.core.logging import logger

class AgentTracer:
    """
    Handles Live Reasoning streams (Execution Traces) for the Agentic Loop.
    Emits data to both the terminal console (colored text) and WebUI (SSE).
    """
    
    # ANSI Colors for Terminal
    COLOR_AGENT = '\033[96m'  # Cyan
    COLOR_TOOL  = '\033[93m'  # Yellow
    COLOR_ERROR = '\033[91m'  # Red
    COLOR_SUCCESS = '\033[92m'# Green
    COLOR_RESET = '\033[0m'

    @staticmethod
    def emit(state_manager, msg: str, level: str = "info"):
        """
        Emits a trace event.
        :param state_manager: instance of StateManager (or None if CLI only)
        :param msg: The reasoning message (e.g., "Executing Sandbox...")
        :param level: "info", "tool", "error", "success"
        """
        # 1. Terminal Output
        color = AgentTracer.COLOR_AGENT
        prefix = "ðŸ§  [Agent]"
        
        if level == "tool":
            color = AgentTracer.COLOR_TOOL
            prefix = "âš™ï¸ [Tool]"
        elif level == "error":
            color = AgentTracer.COLOR_ERROR
            prefix = "âŒ [Error]"
        elif level == "success":
            color = AgentTracer.COLOR_SUCCESS
            prefix = "âœ… [Success]"
            
        print(f"{color}{prefix} {msg}{AgentTracer.COLOR_RESET}")
        logger.debug("AGENT_TRACE", f"{level.upper()}: {msg}")
        
        # 2. WebUI SSE Event
        if state_manager:
            # We add a special trace event to the state manager queue.
            # The UI endpoint /api/events will stream this.
            state_manager.add_event("agent_trace", {
                "level": level,
                "message": msg
            })
