import os
import json
import subprocess
import threading
import time
from typing import Dict, List, Any

try:
    from zentra.core.logging import logger
    from zentra.core.system import plugin_loader
except ImportError:
    # Standalone support
    class _L:
        def info(self, m): print(f"[MCP] {m}")
        def error(self, m): print(f"[MCP ERR] {m}")
        def debug(self, m): pass
        def warning(self, m): print(f"[MCP WARN] {m}")
    logger = _L()

class MCPProxy:
    """Manages a single MCP server connection via stdio."""
    def __init__(self, name: str, command: str, args: List[str] = [], env: Dict[str, str] = {}):
        self.name = name
        self.command = command
        self.args = args
        self.env = {**os.environ, **env}
        self.process = None
        self.msg_id = 1
        self.tools = []
        self._lock = threading.Lock()
        self._stop_event = None
        self._stderr_thread = None

    def start(self):
        try:
            full_cmd = [self.command] + self.args
            logger.info(f"[MCP:{self.name}] Starting server: {' '.join(full_cmd)}")
            self.process = subprocess.Popen(
                full_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                env=self.env
            )
            # Start stderr reader
            self._stop_event = threading.Event()
            self._stderr_thread = threading.Thread(target=self._read_stderr, daemon=True)
            self._stderr_thread.start()

            # Initialize connection in background to avoid blocking boot
            threading.Thread(target=self._fetch_tools, daemon=True).start()
        except Exception as e:
            logger.error(f"[MCP:{self.name}] Failed to start: {e}")

    def _fetch_tools(self):
        # Small sleep to allow server to print initial startup banners
        time.sleep(2)
        for i in range(5):
            res = self.call("tools/list")
            if res and "result" in res:
                self.tools = res["result"].get("tools", [])
                logger.info(f"[MCP:{self.name}] Discovered {len(self.tools)} tools.")
                return
            if i < 4:
                logger.info(f"[MCP:{self.name}] Tool discovery retry {i+1}/5...")
                time.sleep(3)
        logger.error(f"[MCP:{self.name}] Failed to discover tools after 5 attempts.")

    def call(self, method: str, params: Dict[str, Any] = {}):
        if not self.process or not self.process.stdin or not self.process.stdout: 
            return None
        with self._lock:
            if self.process.poll() is not None:
                logger.error(f"[MCP:{self.name}] Cannot call method '{method}': Process exited with code {self.process.returncode}")
                return None
            try:
                req = {
                    "jsonrpc": "2.0",
                    "method": method,
                    "params": params,
                    "id": self.msg_id
                }
                self.msg_id += 1
                self.process.stdin.write(json.dumps(req) + "\n")
                self.process.stdin.flush()
                
                # Consume lines until we find a JSON response
                # This skips "noise" from CLI wrappers like @smithery/cli or npx
                for _ in range(20): # Limit to 20 lines of noise
                    line = self.process.stdout.readline()
                    if not line: return None
                    line = line.strip()
                    if not line: continue
                    if line.startswith("{"):
                        try:
                            return json.loads(line)
                        except json.JSONDecodeError:
                            logger.debug(f"[MCP:{self.name}] Skipped non-JSON line: {line}")
                            continue
                    else:
                        logger.debug(f"[MCP:{self.name}] Skipped startup noise: {line}")
                return None
            except Exception as e:
                logger.error(f"[MCP:{self.name}] Call error: {e}")
                return None

    def _read_stderr(self):
        """Monitors stderr in a background thread and logs it."""
        if not self.process or not self.process.stderr: return
        while self.process.poll() is None and self._stop_event and not self._stop_event.is_set():
            line = self.process.stderr.readline()
            if not line: break
            line = line.strip()
            if line:
                logger.warning(f"[MCP:{self.name}:stderr] {line}")

    def stop(self):
        if self._stop_event: self._stop_event.set()
        p = self.process
        if p:
            try:
                p.terminate()
                p.wait(timeout=2)
            except:
                pass
            self.process = None

class MCPBridgePlugin:
    """
    Zentra MCP Bridge.
    Acts as a client for external MCP servers and exposes them as native Zentra tools.
    """
    def __init__(self):
        self.tag = "MCP_BRIDGE"
        self.desc = "Bridge to Model Context Protocol (MCP) servers"
        self.proxies: Dict[str, MCPProxy] = {}
        self.initialized = False

    def bootstrap(self, config: Dict[str, Any]):
        """Starts all enabled MCP servers defined in config."""
        if self.initialized: return
        
        mcp_cfg = config.get("plugins", {}).get("MCP_BRIDGE", {})
        servers = mcp_cfg.get("servers", {})
        
        logger.info(f"[MCP_BRIDGE DEMO] Extracted raw config servers: {list(servers.keys())}")
        
        for name, s_cfg in servers.items():
            if not s_cfg.get("enabled", True): 
                logger.info(f"[MCP_BRIDGE DEMO] Skipping {name} because it is disabled.")
                continue
            
            # WINDOWS FIX: Ensure commands use .cmd if applicable
            cmd = s_cfg.get("command")
            if os.name == 'nt' and cmd == 'npx':
                cmd = 'npx.cmd'
                
            proxy = MCPProxy(
                name=name,
                command=cmd,
                args=s_cfg.get("args", []),
                env=s_cfg.get("env", {})
            )
            proxy.start()
            self.proxies[name] = proxy
            logger.info(f"[MCP_BRIDGE DEMO] Proxy object appended for {name}. Total proxies: {len(self.proxies)}")
        
        self.initialized = True
        logger.info(f"[MCP_BRIDGE] Bootstrap complete. {len(self.proxies)} servers connected.")

    # ── Tool Execution Wrapper ───────────────────────────────────────────────
    def execute_mcp_tool(self, server_name: str, tool_name: str, **kwargs):
        """Dynamic entry point for tools called via Function Calling."""
        proxy = self.proxies.get(server_name)
        if not proxy: return f"Error: MCP Server '{server_name}' not found or not connected."
        
        res = proxy.call("tools/call", {"name": tool_name, "arguments": kwargs})
        if not res: return "Error: No response from MCP server."
        if "error" in res: return f"MCP Error: {res['error']}"
        
        # Format the result (usually 'content' list in MCP)
        content = res.get("result", {}).get("content", [])
        output = ""
        for item in content:
            if item.get("type") == "text":
                output += item.get("text", "")
        return output if output else "Tool executed successfully (no output)."

    def search_mcp(self, query: str, registry: str = "smithery"):
        """Searches for MCP servers in the specified registry."""
        import subprocess
        try:
            if registry == "smithery":
                cmd = ["npx.cmd", "-y", "@smithery/cli", "mcp", "search", query]
            else: # mcp-get / mcpskills
                cmd = ["npx.cmd", "-y", "mcp-get", "search", query, "--json"]
                
            res = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if res.returncode != 0:
                return f"Search Error: {res.stderr}"
            return res.stdout
        except Exception as e:
            return f"Search Exception: {e}"

    # ── Zentra Skill Methods ──────────────────────────────────────────────────
    def status(self):
        """Displays the list of active servers and their tools."""
        if not self.proxies: return "No MCP servers connected."
        lines = ["Active MCP Servers:"]
        for name, p in self.proxies.items():
            lines.append(f" - {name} ({len(p.tools)} tools)")
        return "\n".join(lines)

    def list(self):
        """Lists all discovered tools."""
        lines = ["Available MCP Tools:"]
        for p_name, p in self.proxies.items():
            for t in p.tools:
                lines.append(f" [{p_name}] {t.get('name')}: {t.get('description', '')}")
        return "\n".join(lines)

    def reload(self):
        """Restarts all servers and refreshes tools."""
        for p in self.proxies.values(): p.stop()
        self.proxies.clear()
        self.initialized = False
        # We need the real config here, but for now we expect the next call to trigger it
        return "MCP Servers scheduled for reload."

    def get_tool_schemas(self):
        """
        Returns all discovered MCP tools in an OpenAI-compatible function schema format.
        Flattens the namespace so each tool appears as `[server_name]__[tool_name]`.
        """
        schemas = []
        for server_name, proxy in self.proxies.items():
            for t in proxy.tools:
                # Basic MCP tool format: name, description, inputSchema
                tool_name = t.get("name", "")
                
                # Zentra flattens this using double underscore
                flat_name = f"{server_name}__{tool_name}"
                
                schema = {
                    "type": "function",
                    "function": {
                        "name": flat_name,
                        "description": t.get("description", f"MCP Tool: {tool_name} from {server_name}"),
                        "parameters": t.get("inputSchema", {"type": "object", "properties": {}})
                    }
                }
                schemas.append(schema)
        return schemas

# ── Dynamic Tool Injection ───────────────────────────────────────────────────
# Custom tools object to satisfy Zentra's loader
class DynamicTools:
    def __init__(self, bridge: MCPBridgePlugin):
        self._bridge = bridge
        self.tag = "MCP_BRIDGE"
        self.desc = bridge.desc

    def status(self): return self._bridge.status()
    def list(self): return self._bridge.list()
    def reload(self): return self._bridge.reload()
    
    def get_mcp_schemas(self):
        """Hook used by Zentra's plugin_docs.py to merge tools."""
        return self._bridge.get_tool_schemas()

    # NOTE: Zentra's processor looks for methods on this object.
    # To support DYNAMIC tools from MCP servers, we would ideally override __getattr__
    # or populate this object on the fly.
    
    def call_tool(self, server: str, tool: str, arguments_json: str):
        """
        Executes an MCP tool.
        :param server: Name of the MCP server (e.g. 'google-maps')
        :param tool: Name of the tool to call
        :param arguments_json: JSON string with tool arguments
        """
    def call_tool(self, server: str, tool: str, arguments_json: str):
        """
        Executes an MCP tool.
        :param server: Name of the MCP server (e.g. 'google-maps')
        :param tool: Name of the tool to call
        :param arguments_json: JSON string with tool arguments
        """
        try:
            args = json.loads(arguments_json)
        except:
            args = {}
        return self._bridge.execute_mcp_tool(server, tool, **args)

    def search(self, query: str, registry: str = "smithery"):
        """Search for MCP servers on Smithery or MCPSkills (mcp-get)."""
        return self._bridge.search_mcp(query, registry)

bridge_instance = MCPBridgePlugin()
tools = DynamicTools(bridge_instance)

def execute(comando: str) -> str:
    # Legacy support
    return tools.status()

def info() -> dict:
        return {
            "tag": "MCP_BRIDGE",
            "description": tools.desc,
            "commands": {
                "status": "Show status",
                "list": "List tools",
                "call_tool": "Call an MCP tool [server, tool, arguments]",
                "search": "Search for MCP servers [query, registry='smithery'|'mcp-get']"
            }
        }

# Initialization hook
def on_load(config):
    bridge_instance.bootstrap(config)
