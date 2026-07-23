"""
mcp_bridge — Hecos Model Context Protocol Bridge
Public API surface for use by other Hecos modules and routes.
"""

from .constants import (
    MCP_PROTOCOL_VERSION,
    MCP_CALL_TIMEOUT,
    MCP_INIT_TIMEOUT,
)
from .proxy import MCPProxy
from .bridge import MCPBridgePlugin
from .tools import DynamicTools
from .main import bridge_instance, tools, on_load, info, execute

__all__ = [
    "MCPProxy",
    "MCPBridgePlugin",
    "DynamicTools",
    "bridge_instance",
    "tools",
    "on_load",
    "info",
    "execute",
    "MCP_PROTOCOL_VERSION",
    "MCP_CALL_TIMEOUT",
    "MCP_INIT_TIMEOUT",
]
