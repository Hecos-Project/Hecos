"""
routes_packages.py
─────────────────────────────────────────────────────────────────────────────
Hecos WebUI — Package Manager REST API
Orchestrator file.

Endpoints:
  GET  /api/packages                  List all installed packages
  POST /api/packages/install          Upload and install a .hpkg file
  GET  /api/packages/<id>             Get details of a specific package
  GET  /api/packages/<id>/manifest    Get the stored manifest snapshot
  PATCH /api/packages/<id>/status     Enable or disable a package
  DELETE /api/packages/<id>           Uninstall a package

All routes require login.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import os
from hecos.core.logging import logger

from hecos.modules.web_ui.routes_packages_list import register_list_routes
from hecos.modules.web_ui.routes_packages_install import register_install_routes
from hecos.modules.web_ui.routes_packages_manage import register_manage_routes
from hecos.modules.web_ui.routes_packages_search import register_search_routes

def init_package_routes(app, hecos_root: str, cfg_mgr, _log=None):
    """Register all HPM REST routes on the Flask app."""

    log = _log or logger

    # Resolve the actual hecos/ source directory (not the project root)
    _hecos_src = os.path.join(hecos_root, "hecos")
    if not os.path.isdir(_hecos_src):
        _hecos_src = hecos_root  # fallback: already pointing at hecos/

    # Store for use by _refresh_jinja_loader (which is stateless/helper)
    import sys as _sys
    _sys._hecos_src_dir = _hecos_src

    register_list_routes(app, _hecos_src, cfg_mgr, log)
    register_install_routes(app, _hecos_src, cfg_mgr, log)
    register_manage_routes(app, _hecos_src, cfg_mgr, log)
    register_search_routes(app, _hecos_src, cfg_mgr, log)

    log.info("[HPM] Package Manager routes registered.")
