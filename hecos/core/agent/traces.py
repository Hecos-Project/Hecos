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

    # To allow plugins/tools to emit traces without having the state_manager instance
    _current_state_manager = None
    
    @classmethod
    def bind(cls, state_manager):
        """Binds the current session's state manager so tools can emit actions globally."""
        cls._current_state_manager = state_manager

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
        prefix = "🧠 [Agent]"
        
        if level == "tool":
            color = AgentTracer.COLOR_TOOL
            prefix = "⚙️ [Tool]"
        elif level == "error":
            color = AgentTracer.COLOR_ERROR
            prefix = "❌ [Error]"
        elif level == "success":
            color = AgentTracer.COLOR_SUCCESS
            prefix = "✅ [Success]"
            
        print(f"{color}{prefix} {msg}{AgentTracer.COLOR_RESET}")
        logger.debug("AGENT_TRACE", f"{level.upper()}: {msg}")
        
        # 2. WebUI SSE Event
        sm = state_manager or AgentTracer._current_state_manager
        if sm:
            sm.add_event("agent_trace", {
                "level": level,
                "message": msg
            })

    @staticmethod
    def emit_action(tool_name: str, command: str, output: str):
        """
        Emits a physical tool execution log to the terminal and to the WebUI as an Action Console box.
        """
        try:
            from hecos.config.yaml_utils import load_yaml
            from hecos.config.schemas.agent_schema import AgentConfig
            _cfg_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "config", "data", "agent.yaml"))
            if os.path.exists(_cfg_path):
                cfg = load_yaml(_cfg_path, AgentConfig)
                if not getattr(cfg, 'action_console_enabled', True):
                    return
        except Exception:
            pass

        # 1. Terminal Output (Hacker style)
        print(f"\n{AgentTracer.COLOR_TOOL}┌── [ACTION] {tool_name}{AgentTracer.COLOR_RESET}")
        print(f"{AgentTracer.COLOR_AGENT}│ $ {command}{AgentTracer.COLOR_RESET}")
        
        preview = output.strip()
        if len(preview) > 500:
            preview = preview[:500] + "\n...[truncated]"
            
        # Format preview with a pipe prefix
        preview_lines = preview.splitlines()
        for line in preview_lines:
            print(f"│   {line}")
        print(f"{AgentTracer.COLOR_TOOL}└─────────────────────{AgentTracer.COLOR_RESET}\n")
        
        # 2. Web UI Action Console Event
        sm = AgentTracer._current_state_manager
        if sm:
            sm.add_event("action_console", {
                "tool_name": tool_name,
                "command": command,
                "output": output
            })
