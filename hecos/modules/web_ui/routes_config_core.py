"""
routes_config_core.py
─────────────────────────────────────────────────────────────────────────────
Hecos WebUI — Core Configuration Routes
Facade module. Implementations are split across:
- routes_config_api.py (REST API, _build_options_dict)
- routes_config_ui.py (HTML Shell, Panel Discovery)
─────────────────────────────────────────────────────────────────────────────
"""
from hecos.modules.web_ui.routes_config_api import (
    register_config_api_routes,
    _OPTIONS_CACHE,
    _OPTIONS_CACHE_TS,
    _OPTIONS_CACHE_TTL,
    _invalidate_options_cache,
    _build_options_dict
)

from hecos.modules.web_ui.routes_config_ui import (
    register_config_ui_routes,
    _PANEL_MAP,
    _PANELS_NEEDING_OPTIONS,
    _HPM_PANEL_CACHE,
    clear_hpm_panel_cache,
    _discover_hpm_panel
)

def init_config_core_routes(app, cfg_mgr, logger, get_sm=None):
    """Register core UI and system configuration routes."""
    # Register REST API endpoints
    register_config_api_routes(app, cfg_mgr, get_sm)
    
    # Register UI rendering endpoints
    register_config_ui_routes(app, cfg_mgr, get_sm)
