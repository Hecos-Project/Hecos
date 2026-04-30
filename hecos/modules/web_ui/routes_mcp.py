from flask import jsonify
from hecos.core.system import module_loader

def init_mcp_routes(app, cfg_mgr, logger):
    @app.route("/api/mcp/inventory", methods=["GET"])
    def get_mcp_inventory():
        """Returns the list of all discovered MCP tools for the UI."""
        try:
            mcp_module = module_loader.get_plugin_module("MCP_BRIDGE", legacy=False)
            if not mcp_module or not hasattr(mcp_module, "bridge_instance"):
                return jsonify({"ok": True, "servers": {}})
            
            bridge = mcp_module.bridge_instance
            inventory = {}
            
            for name, proxy in bridge.proxies.items():
                # Check status
                status = "unknown"
                if proxy.process:
                    if proxy.process.poll() is not None:
                        status = "crashed"
                    else:
                        status = getattr(proxy, "status", "connected")
                else:
                    status = "disconnected"
                
                inventory[name] = {
                    "status": status,
                    "tools": proxy.tools
                }
                
            return jsonify({"ok": True, "servers": inventory})
        except Exception as e:
            logger.error(f"[WebUI] /api/mcp/inventory error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/mcp/reload", methods=["POST"])
    def reload_mcp_bridge():
        """Hot-syncs the MCP bridge with the current saved configuration.
        Starts new servers and stops removed ones without restarting Hecos."""
        try:
            mcp_module = module_loader.get_plugin_module("MCP_BRIDGE", legacy=False)
            if not mcp_module or not hasattr(mcp_module, "bridge_instance"):
                return jsonify({"ok": False, "error": "MCP Bridge module not loaded"}), 404
            
            config = cfg_mgr.reload()
            bridge = mcp_module.bridge_instance
            bridge.sync_from_config(config)

            # Return updated inventory after sync
            inventory = {}
            for name, proxy in bridge.proxies.items():
                status = getattr(proxy, "status", "starting")
                inventory[name] = {"status": status, "tools": proxy.tools}

            return jsonify({"ok": True, "servers": inventory})
        except Exception as e:
            logger.error(f"[WebUI] /api/mcp/reload error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

