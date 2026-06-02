"""
Hecos Flows — Visual Flow Orchestration Engine
============================================================
Turns Hecos into a fully autonomous Operating Layer by letting
users build, schedule, and run multi-step pipelines via:
  - Natural Language (voice or text → LLM compiler → YAML)
  - Visual node-graph canvas (LiteGraph.js)
  - Direct YAML text editing

All three representations are bidirectionally synced.
"""

from .main import get_plugin, info, status

__all__ = ["get_plugin", "info", "status"]
