"""
MODULE: Agent Config Schema
DESCRIPTION: Pydantic v2 model for config/agent.yaml
"""

from pydantic import BaseModel


class AgentConfig(BaseModel):
    """Root schema for config/agent.yaml"""
    enabled: bool = True
    max_iterations: int = 5
    verbose_traces: bool = True
    action_console_enabled: bool = True
    autonomy_trust_mode: str = "ask"
    autonomy_max_installs: int = 3
    autonomy_reflection: str = "daily"
