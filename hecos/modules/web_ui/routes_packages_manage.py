"""
routes_packages_manage.py
─────────────────────────────────────────────────────────────────────────────
Get, update status, and delete packages.
"""
from __future__ import annotations
import os
from flask import jsonify, request
from flask_login import login_required

from hecos.modules.web_ui.routes_packages_helpers import (
    _get_hpm_components,
    _refresh_jinja_loader,
    _hpm_event_broadcast
)
from .routes_packages_manage_info import register_manage_info_routes
from .routes_packages_manage_config import register_manage_config_routes
from .routes_packages_manage_status import register_manage_status_routes, _invalidate_all_caches, _hot_reload_registry
from .routes_packages_manage_uninstall import register_manage_uninstall_routes

def register_manage_routes(app, _hecos_src: str, cfg_mgr, log):
    register_manage_info_routes(app, _hecos_src, cfg_mgr, log)
    register_manage_config_routes(app, _hecos_src, cfg_mgr, log)
    register_manage_status_routes(app, _hecos_src, cfg_mgr, log)
    register_manage_uninstall_routes(app, _hecos_src, cfg_mgr, log)
