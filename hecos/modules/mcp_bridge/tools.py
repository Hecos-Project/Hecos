import json
from .bridge import MCPBridgePlugin

class DynamicTools:
    """Hecos module interface wrapping MCPBridgePlugin."""

    def __init__(self, bridge: MCPBridgePlugin):
        self._bridge = bridge
        self.tag     = "MCP_BRIDGE"
        self.desc    = bridge.desc

    def status(self) -> str:
        return self._bridge.status()

    def list(self) -> str:
        return self._bridge.list()

    def reload(self) -> str:
        return self._bridge.reload()

    def get_mcp_schemas(self) -> list:
        return self._bridge.get_tool_schemas()

    def call_tool(self, server: str, tool: str, arguments_json: str = "{}") -> str:
        try:
            args = json.loads(arguments_json)
        except json.JSONDecodeError:
            return f"Error: arguments_json is not valid JSON: {arguments_json!r}"
        return self._bridge.execute_mcp_tool(server, tool, **args)

    def search(self, query: str, registry: str = "smithery") -> str:
        return self._bridge.search_mcp(query, registry)
