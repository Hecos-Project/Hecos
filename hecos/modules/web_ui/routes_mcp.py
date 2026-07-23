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
                    "tools": proxy.tools,
                    "error": getattr(proxy, "last_error", "")
                }
                
            return jsonify({"ok": True, "servers": inventory})
        except Exception as e:
            logger.error(f"[WebUI] /api/mcp/inventory error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/mcp/config", methods=["POST"])
    def save_mcp_config():
        """Saves ONLY the MCP_BRIDGE plugin block directly to disk.
        This bypasses buildPayload() entirely, which was overwriting MCP changes
        by reconstructing plugins from DOM elements that don't include the MCP panel.
        """
        from flask import request
        try:
            data = request.get_json(force=True)
            if not isinstance(data, dict):
                return jsonify({"ok": False, "error": "Invalid payload"}), 400

            # Read current full config, then patch only the MCP_BRIDGE section
            current = cfg_mgr.reload()
            current.setdefault("plugins", {})["MCP_BRIDGE"] = data

            saved = cfg_mgr.update_config(current)
            if not saved:
                return jsonify({"ok": False, "error": "Config write failed"}), 500

            logger.info("MCP_BRIDGE", f"MCP config saved — {len(data.get('servers', {}))} server(s).")

            # Also hot-sync the bridge immediately
            mcp_module = module_loader.get_plugin_module("MCP_BRIDGE", legacy=False)
            if mcp_module and hasattr(mcp_module, "bridge_instance"):
                mcp_module.bridge_instance.sync_from_config(cfg_mgr.config)

            return jsonify({"ok": True})
        except Exception as e:
            logger.error(f"[WebUI] /api/mcp/config error: {e}")
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
                inventory[name] = {
                    "status": status,
                    "tools": proxy.tools,
                    "error": getattr(proxy, "last_error", "")
                }

            return jsonify({"ok": True, "servers": inventory})
        except Exception as e:
            logger.error(f"[WebUI] /api/mcp/reload error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/mcp/restart_server", methods=["POST"])
    def restart_mcp_server():
        """Forces a hard restart of a single MCP server process."""
        try:
            data = request.get_json(force=True)
            name = data.get("name")
            if not name:
                return jsonify({"ok": False, "error": "Server name missing"}), 400

            mcp_module = module_loader.get_plugin_module("MCP_BRIDGE", legacy=False)
            if not mcp_module or not hasattr(mcp_module, "bridge_instance"):
                return jsonify({"ok": False, "error": "MCP Bridge not active"}), 404

            bridge = mcp_module.bridge_instance
            if name in bridge.proxies:
                bridge.proxies[name].stop()
                del bridge.proxies[name]

            # Re-sync to spawn it again
            bridge.sync_from_config(cfg_mgr.config)
            return jsonify({"ok": True})
        except Exception as e:
            logger.error(f"[WebUI] /api/mcp/restart_server error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

