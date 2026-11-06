"""
MODULE: Agent Config Schema
DESCRIPTION: Pydantic v2 model for config/agent.yaml
"""

from typing import Literal
from pydantic import BaseModel, Field, model_validator


class AgentConfig(BaseModel):
    """Root schema for config/agent.yaml"""
    enabled: bool = True
    max_iterations: int = Field(default=15, ge=1, le=50)
    verbose_traces: bool = True
    trace_mode: Literal["off", "minimal", "detailed"] = "detailed"
    trace_after_done: Literal["summary", "hide", "expanded"] = "summary"
    trace_show_args: bool = True
    trace_persist_history: bool = True
    cli_traces_enabled: bool = True
    action_console_enabled: bool = True
    action_console_mode: Literal["inline", "chat", "off"] = "inline"

    @model_validator(mode="before")
    @classmethod
    def _sync_legacy_fields(cls, data):
        if not isinstance(data, dict):
            return data
        out = dict(data)

        # Clamp max_iterations safely
        if "max_iterations" in out:
            try:
                out["max_iterations"] = max(1, min(50, int(out["max_iterations"])))
            except Exception:
                out["max_iterations"] = 15

        # Migrate / sync trace_mode <-> verbose_traces
        if "trace_mode" not in out:
            if out.get("verbose_traces") is False:
                out["trace_mode"] = "off"
            else:
                out["trace_mode"] = "detailed"
        out["verbose_traces"] = (out.get("trace_mode") != "off")

        # Migrate / sync action_console_mode <-> action_console_enabled
        if "action_console_mode" not in out:
            if out.get("action_console_enabled") is False:
                out["action_console_mode"] = "off"
            else:
                out["action_console_mode"] = "inline"
        out["action_console_enabled"] = (out.get("action_console_mode") != "off")

        return out
