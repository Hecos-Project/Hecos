"""
routes_widgets.py
─────────────────────────────────────────────────────────────────────────────
Hecos WebUI — Widget Manager Orchestrator
Provides REST endpoints to list, reorder, toggle widget visibility, and
handle the Control Room layout logic. Split into sub-modules for easier maintenance.
─────────────────────────────────────────────────────────────────────────────
"""
from hecos.core.logging import logger

from .routes_widgets_api import init_widget_api_routes
from .routes_widgets_sidebar import init_widget_sidebar_routes
from .routes_widgets_room import init_widget_room_routes
from .routes_widgets_aesthetics import init_widget_aesthetics_routes

def init_widget_routes(app, config_manager, logger_ref=None):
    """Registers all /api/widgets/* routes via sub-modules."""

    _log = logger_ref or logger

    def _get_config():
        return config_manager.config if config_manager else {}

    def _save_config():
        """Saves current config and broadcasts a refresh signal."""
        res = config_manager.save()
        import sys
        print(f"[DEBUG-WIDGETS] save() result: {res}", file=sys.stderr)
        if res:
            try:
                from .server import get_state_manager
                sm = get_state_manager()
                if sm:
                    sm.add_event("widgets_refresh")
            except Exception as e:
                _log.warning(f"[Widgets] Failed to trigger SSE refresh: {e}")
        return res

    # 1. Base API routes (list, set order)
    init_widget_api_routes(app, config_manager, _log, _get_config, _save_config)

    # 2. Sidebar Navigation overrides
    init_widget_sidebar_routes(app, config_manager, _log, _get_config, _save_config)

    # 3. Control Room Grid Layout
    init_widget_room_routes(app, config_manager, _log, _get_config, _save_config)

    # 4. Themes and Aesthetics
    init_widget_aesthetics_routes(app, config_manager, _log, _get_config, _save_config)

    _log.debug("[WebUI] Modular Widget routes fully registered.")
