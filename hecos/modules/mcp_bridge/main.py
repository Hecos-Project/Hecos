"""
mcp_bridge/main.py
──────────────────
Hecos MCP Bridge — thin entry point.
All logic lives in the sub-modules:
  constants.py  → timeouts / protocol settings
  proxy.py      → MCPProxy (stdio process + reader/watchdog threads)
  bridge.py     → MCPBridgePlugin (multi-server manager)
  tools.py      → DynamicTools (Hecos module interface)
"""

from .bridge import MCPBridgePlugin
from .tools import DynamicTools

# ── Module-level singletons (used by routes_mcp.py) ─────────────────────────
bridge_instance = MCPBridgePlugin()
tools = DynamicTools(bridge_instance)


# ── Hecos module hooks ───────────────────────────────────────────────────────

def execute(comando: str) -> str:
    """Legacy dispatch hook called by Hecos core."""
    cmd = comando.strip().lower()
    if cmd == "list":
        return tools.list()
    if cmd == "reload":
        return tools.reload()
    return tools.status()


def info() -> dict:
    return {
        "tag":         "MCP_BRIDGE",
        "description": tools.desc,
        "commands": {
            "status":    "Show status of all connected MCP servers",
            "list":      "List all available tools from all MCP servers",
            "reload":    "Fully restart all MCP servers from saved config",
            "call_tool": "Call an MCP tool: server, tool, arguments_json (JSON string)",
            "search":    "Search for MCP servers: query, registry='smithery'|'mcp-get'",
        },
    }


def on_load(config: dict):
    """Initialization hook called by Hecos bootstrapper on startup."""
    bridge_instance.bootstrap(config)
