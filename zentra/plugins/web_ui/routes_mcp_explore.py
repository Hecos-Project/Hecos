import subprocess
import json
import os
from flask import request, jsonify

def init_mcp_explore_routes(app, cfg_mgr, logger):
    @app.route("/api/mcp/explore", methods=["GET"])
    def explore_mcp_servers():
        """
        Searches the Smithery.ai registry using npx @smithery/cli.
        Usage: /api/mcp/explore?q=term
        """
        query = request.args.get("q", "").strip()
        registry = request.args.get("reg", "smithery").lower()
        if not query:
            return jsonify({"ok": True, "results": []})

        try:
            logger.info(f"[MCP-EXPLORE] Searching {registry} for: '{query}'")
            npx_cmd = "npx.cmd" if os.name == "nt" else "npx"
            
            if registry == "mcp-get":
                cmd = [npx_cmd, "-y", "mcp-get", "search", query, "--json"]
            else:
                cmd = [npx_cmd, "-y", "@smithery/cli", "mcp", "search", query]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                encoding='utf-8',
                timeout=20
            )

            if result.returncode != 0:
                logger.error(f"[MCP-EXPLORE] {registry} CLI error: {result.stderr}")
                return jsonify({"ok": False, "error": f"Search on {registry} failed."}), 500

            results = []
            if registry == "mcp-get":
                try:
                    # mcp-get returns a single JSON object with a "data" list
                    data = json.loads(result.stdout)
                    results = data.get("data", [])
                except json.JSONDecodeError:
                    logger.error("[MCP-EXPLORE] Failed to parse mcp-get JSON output")
            else:
                # Smithery returns NDJSON (one object per line)
                for line in result.stdout.strip().split("\n"):
                    if not line.strip() or line.startswith("-"): continue
                    try:
                        data = json.loads(line)
                        results.append(data)
                    except json.JSONDecodeError:
                        continue

            logger.info(f"[MCP-EXPLORE] Found {len(results)} results in {registry} for '{query}'")
            return jsonify({"ok": True, "results": results})

        except subprocess.TimeoutExpired:
            return jsonify({"ok": False, "error": "Search timed out. Please try again."}), 504
        except Exception as e:
            logger.error(f"[MCP-EXPLORE] Critical error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500
