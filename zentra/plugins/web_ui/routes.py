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
from .routes_security import init_security_routes
from .routes_keys import init_keys_routes
from .routes_docs import init_docs_routes

def init_routes(app, cfg_mgr, root_dir, logger, get_sm=None):
    """Initializes all component routes for the Web UI."""
    init_config_routes(app, cfg_mgr, root_dir, logger, get_sm)
    init_audio_routes(app, cfg_mgr, root_dir, logger, get_sm)
    init_media_routes(app, cfg_mgr, root_dir, logger, get_sm)
    init_system_routes(app, cfg_mgr, root_dir, logger, get_sm)
    init_users_routes(app, logger)
    init_security_routes(app, logger)
    init_keys_routes(app, logger)
    init_docs_routes(app, cfg_mgr, root_dir, logger)
    
    # Zentra Drive — HTTP File Manager
    try:
        from . . drive.routes import init_drive_routes
        init_drive_routes(app, logger)
    except Exception as e:
        try:
            from zentra.plugins.drive.routes import init_drive_routes
            init_drive_routes(app, logger)
        except Exception:
            logger.warning(f"[WebUI] Zentra Drive non disponibile: {e}")

    # Remote Triggers — Tasti hardware iPhone e Webhooks Arduino 
    try:
        from . . remote_triggers.routes import init_remote_triggers_routes
        init_remote_triggers_routes(app, logger)
    except Exception as e:
        try:
            from zentra.plugins.remote_triggers.routes import init_remote_triggers_routes
            init_remote_triggers_routes(app, logger)
        except Exception:
            pass

