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
from hecos.modules.web_ui.routes_packages_store import register_store_routes

def init_package_routes(app, hecos_root: str, cfg_mgr, _log=None):
    """Register all HPM REST routes on the Flask app."""

    log = _log or logger

    # Resolve the actual hecos/ source directory (not the project root)
    _hecos_src = os.path.join(hecos_root, "hecos")
    if not os.path.isdir(_hecos_src):
        _hecos_src = hecos_root  # fallback: already pointing at hecos/

    # Store for use by _refresh_jinja_loader and _get_hpm_components
    import sys as _sys
    _sys._hecos_src_dir = _hecos_src
    _sys._hecos_cfg_mgr = cfg_mgr

    register_list_routes(app, _hecos_src, cfg_mgr, log)
    register_install_routes(app, _hecos_src, cfg_mgr, log)
    register_manage_routes(app, _hecos_src, cfg_mgr, log)
    register_search_routes(app, _hecos_src, cfg_mgr, log)
    register_store_routes(app, _hecos_src, cfg_mgr, log)

    # Automatically load standalone API routes for HPM packages
    try:
        from hecos.core.package_manager.registry import PackageRegistry
        data_dir = os.path.join(hecos_root, "hecos", "data")
        if not os.path.isdir(data_dir):
            data_dir = os.path.join(hecos_root, "data")
        reg = PackageRegistry(data_dir)
        import json as _json
        for pkg in reg.list_all():
            if pkg.get("status") == "disabled":
                continue
            manifest = pkg.get("manifest_snapshot") or {}
            if isinstance(manifest, str):
                try: manifest = _json.loads(manifest)
                except: manifest = {}
            
            cp = manifest.get("config_panel", {})
            api_routes_file = cp.get("api_routes_file")
            
            if api_routes_file:
                plugin_id = pkg["id"]
                plugin_path = os.path.join(hecos_root, "hecos", "plugins", plugin_id)
                if not os.path.isdir(plugin_path):
                    plugin_path = os.path.join(hecos_root, "plugins", plugin_id)
                abs_route_path = os.path.join(plugin_path, api_routes_file)
                
                if os.path.isfile(abs_route_path):
                    import importlib.util
                    spec = importlib.util.spec_from_file_location(f"plugin_routes_{plugin_id}", abs_route_path)
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    if hasattr(mod, 'init_plugin_routes'):
                        try:
                            # HPM plugins routes must accept (app, cfg_mgr, hecos_root, logger)
                            mod.init_plugin_routes(app, cfg_mgr, hecos_root, log)
                            log.info(f"[HPM:Routes] Registered standalone API routes for '{plugin_id}'")
                        except Exception as e:
                            log.error(f"[HPM:Routes] Error initializing routes for '{plugin_id}': {e}")
    except Exception as e:
        log.error(f"[HPM:Routes] Failed to auto-discover HPM API routes: {e}")

    log.info("[HPM] Package Manager routes registered.")
