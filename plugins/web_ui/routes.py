"""
MODULE: Web UI Routes Faculty
DESCRIPTION: Main routing facade for the Zentra Core WebUI Plugin.
             Sub-routes have been split into:
             - routes_config.py
             - routes_audio.py
             - routes_media.py
             - routes_system.py
"""

from .routes_config import init_config_routes
from .routes_audio import init_audio_routes
from .routes_media import init_media_routes
from .routes_system import init_system_routes
from .routes_users import init_users_routes

def init_routes(app, cfg_mgr, root_dir, logger, get_sm=None):
    """Initializes all component routes for the Web UI."""
    init_config_routes(app, cfg_mgr, root_dir, logger, get_sm)
    init_audio_routes(app, cfg_mgr, root_dir, logger, get_sm)
    init_media_routes(app, cfg_mgr, root_dir, logger, get_sm)
    init_system_routes(app, cfg_mgr, root_dir, logger, get_sm)
    init_users_routes(app, logger)
    
    # Zentra Drive — HTTP File Manager
    try:
        from plugins.drive.routes import init_drive_routes
        init_drive_routes(app, logger)
    except Exception as e:
        logger.warning(f"[WebUI] Zentra Drive non disponibile: {e}")

