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
            elif registry == "github":
                try:
                    import urllib.request
                    url = f"https://api.github.com/search/repositories?q={query}+topic:mcp-server&sort=stars"
                    req = urllib.request.Request(url, headers={"User-Agent": "Hecos-Core"})
                    with urllib.request.urlopen(req, timeout=10) as response:
                        data = json.loads(response.read())
                        for repo in data.get("items", []):
                            results.append({
                                "name": repo["full_name"],
                                "description": repo["description"] or "MCP Server repository",
                                "qualifiedName": f"github:{repo['full_name']}",
                                "downloads": repo["stargazers_count"],
                                "homepage": repo["html_url"],
                                "author": repo.get("owner", {}).get("login", "")
                            })
                except Exception as e:
                    logger.error(f"[MCP-EXPLORE] GitHub API error: {e}")
            elif registry == "huggingface":
                try:
                    import urllib.request
                    url = f"https://huggingface.co/api/spaces?search={query}"
                    req = urllib.request.Request(url, headers={"User-Agent": "Hecos-Core"})
                    with urllib.request.urlopen(req, timeout=10) as response:
                        data = json.loads(response.read())
                        for space in data[:15]:
                            results.append({
                                "name": space["id"],
                                "description": f"Hugging Face Space ({space.get('sdk', 'mcp')})",
                                "qualifiedName": f"hf:{space['id']}",
                                "downloads": space.get("likes", 0),
                                "homepage": f"https://huggingface.co/spaces/{space['id']}",
                                "author": space.get("author", space["id"].split("/")[0])
                            })
                except Exception as e:
                    logger.error(f"[MCP-EXPLORE] Hugging Face API error: {e}")
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
