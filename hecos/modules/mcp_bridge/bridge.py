import os
import json
import subprocess
from typing import Dict, List, Any

from .constants import MCP_REMOTE_BASE_PORT, MCP_REMOTE_PORT_RANGE
from .config_manager import get_config as _get_mcp_config

try:
    from hecos.core.logging import logger
except ImportError:
    class _L:
        def info(self, m): print(f"[MCP] {m}")
        def error(self, m): print(f"[MCP ERR] {m}")
        def debug(self, m): pass
        def warning(self, m): print(f"[MCP WARN] {m}")
    logger = _L()

from .proxy import MCPProxy

class MCPBridgePlugin:
    """
    Hecos MCP Bridge.
    Acts as a client for external MCP servers and exposes them as native Hecos tools.
    """

    def __init__(self):
        self.tag  = "MCP_BRIDGE"
        self.desc = "Bridge to Model Context Protocol (MCP) servers"
        self.proxies: Dict[str, MCPProxy] = {}
        self.initialized = False
        self._last_config: Dict[str, Any] = {}

    @staticmethod
    def _assign_port(server_name: str) -> int:
        """Assigns a stable unique port for an mcp-remote subprocess.
        Uses a hash of the server name in the range [MCP_REMOTE_BASE_PORT, base+range)."""
        slot = hash(server_name) % MCP_REMOTE_PORT_RANGE
        return MCP_REMOTE_BASE_PORT + abs(slot)

    def bootstrap(self, config: Dict[str, Any] = None):
        """Called by Hecos bootstrapper on startup. `config` ignored — we read our own file."""
        if self.initialized:
            return
        self.sync_from_config()

    def sync_from_config(self, config: Dict[str, Any] = None):
        """Reload server list from the package's own mcp_bridge.toml.
        The `config` parameter is accepted for backwards-compat but ignored."""
        mcp_cfg = _get_mcp_config()

        if not mcp_cfg.get("enabled", True):
            logger.info("[MCP_BRIDGE] Bridge is disabled in config -- skipping sync.")
            return

        desired = mcp_cfg.get("servers", {})

        # Stop removed/disabled
        removed = [n for n in list(self.proxies.keys())
                   if n not in desired or not desired[n].get("enabled", True)]
        for name in removed:
            logger.info("MCP_BRIDGE", f"Stopping server: {name}")
            self.proxies[name].stop()
            del self.proxies[name]

        # Start new or crashed servers
        for name, s_cfg in desired.items():
            if not s_cfg.get("enabled", True):
                continue
            if name in self.proxies:
                proxy = self.proxies[name]
                if proxy.is_alive():
                    continue  # healthy, leave alone
                if proxy.status == "failed":
                    logger.warning("MCP_BRIDGE",
                        f"Server {name!r} is in 'failed' state (crash limit reached). "
                        "Skipping restart. Restart Hecos to retry.")
                    continue  # don't bypass the crash cap
                # crashed but not given up; clean up before restart
                proxy.stop()
                del self.proxies[name]


            cmd = s_cfg.get("command")
            args = s_cfg.get("args", [])
            env = s_cfg.get("env", {})

            # ── HTTP/remote server: wrap with mcp-remote ──────────────────────
            if s_cfg.get("type") == "http":
                url = s_cfg.get("url", "").strip()
                if not url:
                    logger.error("MCP_BRIDGE", f"Server {name!r} has type=http but no 'url' field. Skipping.")
                    continue
                port = self._assign_port(name)
                npx = "npx.cmd" if os.name == "nt" else "npx"
                cmd  = npx
                args = ["-y", "mcp-remote@latest", url, str(port)]
                env  = {**env, **s_cfg.get("env", {})}
                logger.info("MCP_BRIDGE",
                    f"[{name}] HTTP server → mcp-remote {url} on port {port}")
            else:
                # ── stdio server (default) ────────────────────────────────────
                if os.name == "nt" and cmd == "npx":
                    cmd = "npx.cmd"

            try:
                proxy = MCPProxy(
                    name=name,
                    command=cmd,
                    args=args,
                    env=env,
                )
                proxy.start()
                self.proxies[name] = proxy
                logger.info("MCP_BRIDGE", f"Started server: {name}")
            except Exception as e:
                logger.error("MCP_BRIDGE", f"Failed to start server {name}: {e}")

        self.initialized = True
        logger.info("MCP_BRIDGE", f"Sync complete -- active: {list(self.proxies.keys())}")

    def execute_mcp_tool(self, server_name: str, tool_name: str, **kwargs) -> str:
        proxy = self.proxies.get(server_name)
        if not proxy:
            return f"Error: MCP server {server_name!r} not found or not connected."
        if not proxy.is_alive():
            return f"Error: MCP server {server_name!r} is not running (status: {proxy.status})."

        res = proxy.call("tools/call", {"name": tool_name, "arguments": kwargs})
        if res is None:
            return "Error: No response from MCP server (timeout or connection lost)."
        if "error" in res:
            err = res["error"]
            return f"MCP Error [{err.get('code', '?')}]: {err.get('message', str(err))}."

        content = res.get("result", {}).get("content", [])
        output = "".join(item.get("text", "") for item in content if item.get("type") == "text")
        return output if output else "Tool executed successfully (no text output)."

    def search_mcp(self, query: str, registry: str = "smithery") -> str:
        npx = "npx.cmd" if os.name == "nt" else "npx"
        try:
            if registry == "smithery":
                cmd = [npx, "-y", "@smithery/cli", "mcp", "search", query]
            else:
                cmd = [npx, "-y", "mcp-get", "search", query, "--json"]

            res = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=30)
            if res.returncode != 0:
                return f"Search error: {res.stderr.strip()}"
            return res.stdout
        except subprocess.TimeoutExpired:
            return "Search error: registry lookup timed out."
        except Exception as e:
            return f"Search exception: {e}"

    def status(self) -> str:
        if not self.proxies:
            return "No MCP servers configured."
        lines = ["Active MCP Servers:"]
        for name, p in self.proxies.items():
            alive = "OK" if p.is_alive() else "DOWN"
            lines.append(f"  [{alive}] {name} -- {p.status} ({len(p.tools)} tools)")
        return "\n".join(lines)

    def list(self) -> str:
        lines = ["Available MCP Tools:"]
        for p_name, p in self.proxies.items():
            if not p.tools:
                lines.append(f"  [{p_name}] (no tools -- status: {p.status})")
                continue
            for t in p.tools:
                lines.append(f"  [{p_name}] {t.get('name')}: {t.get('description', '(no description)')}")
        return "\n".join(lines) if len(lines) > 1 else "No tools discovered yet."

    def reload(self) -> str:
        logger.info("MCP_BRIDGE", "Full reload requested.")
        for proxy in self.proxies.values():
            proxy.stop()
        self.proxies.clear()
        self.initialized = False
        # Clear global crash counter so previously-failed servers get a fresh start
        from .proxy import _GLOBAL_RESTART_COUNTS, _GLOBAL_RESTART_LOCK
        with _GLOBAL_RESTART_LOCK:
            _GLOBAL_RESTART_COUNTS.clear()
        self.sync_from_config()
        return f"MCP Bridge reloaded -- {len(self.proxies)} server(s) starting."

    def get_tool_schemas(self) -> list:
        schemas = []
        for server_name, proxy in self.proxies.items():
            for t in proxy.tools:
                tool_name = t.get("name", "")
                schemas.append({
                    "type": "function",
                    "function": {
                        "name":        f"{server_name}__{tool_name}",
                        "description": t.get("description", f"MCP tool {tool_name!r} from {server_name!r}"),
                        "parameters":  t.get("inputSchema", {"type": "object", "properties": {}}),
                    },
                })
        return schemas
