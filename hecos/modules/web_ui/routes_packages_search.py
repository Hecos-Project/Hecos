"""
routes_packages_search.py
─────────────────────────────────────────────────────────────────────────────
Search remote package registry.
"""
from __future__ import annotations
from flask import jsonify, request
from flask_login import login_required

def register_search_routes(app, _hecos_src: str, cfg_mgr, log):

    @app.route("/api/packages/remote/search", methods=["GET"])
    @login_required
    def api_remote_search():
        """
        STUB: Search the remote package registry.
        Returns empty results until the remote registry is implemented.
        """
        from hecos.core.package_manager.remote_registry import RemoteRegistryClient
        client = RemoteRegistryClient()
        query = request.args.get("q", "")
        results = client.search(query=query)
        return jsonify({
            "ok": True,
            "results": results,
            "remote_available": client.is_available,
        })
