"""
routes_config.py
─────────────────────────────────────────────────────────────────────────────
Hecos WebUI — Configuration Orchestrator
To improve maintainability and prevent persistence race conditions, the UI
config routes have been split into domain-specific sub-modules.
This file acts as a lightweight proxy, importing and registering them all.
─────────────────────────────────────────────────────────────────────────────
"""

from .routes_config_core import init_config_core_routes
from .routes_config_media import init_config_media_routes
from .routes_config_agent import init_config_agent_routes
from .routes_config_routing import init_config_routing_routes
from .routes_config_utils import init_config_utils_routes

def init_config_routes(app, cfg_mgr, root_dir, logger, get_sm=None):
    """
    Registers all configuration endpoints by delegating to specialized
    sub-modules to ensure clear separation of concerns.
    """
    # 1. Main UI and System Config (system.yaml)
    init_config_core_routes(app, cfg_mgr, logger, get_sm)

    # 2. Media Player Config (media.yaml / plugins.MEDIA_PLAYER)
    init_config_media_routes(app, logger)

    # 3. Agent Config (agent.yaml)
    init_config_agent_routes(app, root_dir, logger)

    # 4. Routing Overrides Config (routing_overrides.yaml)
    init_config_routing_routes(app, root_dir, logger)

    # 5. UI Utilities (Plugin Registry, Window State)
    init_config_utils_routes(app, root_dir, logger)

    logger.debug("[WebUI] Modular configuration routes fully registered.")
