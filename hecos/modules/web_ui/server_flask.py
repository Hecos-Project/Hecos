"""
WEB_UI Plugin — Flask Core App Generator
Isolates Flask app creation, blueprint mounting, WebUI extension template loading,
logging configuration, and auth initialization.
"""
import os
from flask import Flask, request, redirect, url_for, jsonify
from flask_login import LoginManager, current_user

def create_flask_app(config_manager, root_dir, logger, get_state_manager):
    """
    Create, configure, and return the Flask application object.
    """
    from hecos.core.i18n.translator import t
    from hecos.core.system.version import VERSION
    from hecos.core.auth.auth_manager import auth_mgr

    base_dir = os.path.dirname(__file__)
    tpl_dir = os.path.join(base_dir, "templates")
    stc_dir = os.path.join(base_dir, "static")
    
    app = Flask("hecos.modules.web_ui", 
                template_folder=tpl_dir, 
                static_folder=stc_dir,
                static_url_path='/static')
    
    app.hecos_config_manager = config_manager
    
    # FIX: Force CSS/JS mimetypes
    import mimetypes
    mimetypes.add_type('text/css', '.css')
    mimetypes.add_type('application/javascript', '.js')
    
    # Inject translation system and version into Jinja2 templates
    app.jinja_env.globals.update(t=t, version=VERSION)

    # ── Extend Jinja loader to include WEB_UI extension template dirs ──
    try:
        from jinja2 import FileSystemLoader, ChoiceLoader
        _ext_root = os.path.join(base_dir, "extensions")
        _extra_loaders = []
        if os.path.isdir(_ext_root):
            for _ext_name in os.listdir(_ext_root):
                _ext_tpl = os.path.join(_ext_root, _ext_name, "templates")
                if os.path.isdir(_ext_tpl):
                    _extra_loaders.append(FileSystemLoader(_ext_tpl))
        if _extra_loaders:
            app.jinja_loader = ChoiceLoader([app.jinja_loader] + _extra_loaders)
    except Exception as _jinja_e:
        logger.warning(f"[WebUI] Could not extend Jinja loader: {_jinja_e}")

    # --- HECOS AUTH SYSTEM ---
    app.secret_key = config_manager.config.get("system", {}).get("flask_secret_key", "hecos_default_secret_key_84nd")
    
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "login_page"

    @login_manager.user_loader
    def load_user(user_id):
        return auth_mgr.get_user_by_id(user_id)

    @app.before_request
    def require_login():
        exempt_paths = ['/login', '/logout', '/static', '/assets', '/favicon.ico']
        if any(request.path.startswith(p) for p in exempt_paths): return
        
        if not current_user.is_authenticated:
            if request.path.startswith('/api/') or request.path.startswith('/hecos/api/'):
                return jsonify({"ok": False, "error": "Authentication required. Please login."}), 401
            return redirect(url_for('login_page'))

    # Get debug state from system config
    debug_on = config_manager.config.get("system", {}).get("flask_debug", False)

    import logging as _lg
    class _ProtocolMismatchFilter(_lg.Filter):
        def filter(self, record):
            msg = record.getMessage()
            return not ("Bad request version" in msg or
                        "Bad request syntax" in msg or
                        "Bad HTTP/0.9 request" in msg)

    wz_log = _lg.getLogger("werkzeug")
    wz_log.addFilter(_ProtocolMismatchFilter())
    if not debug_on:
        try:
            wz_log.setLevel(_lg.ERROR)
            app.logger.disabled = True
        except Exception: pass
    else:
        wz_log.setLevel(_lg.INFO)
        wz_log.propagate = True

    # Register all routes
    from .routes import init_routes
    init_routes(app, config_manager, root_dir, logger, get_state_manager)
    
    from .routes_logs import init_log_routes
    init_log_routes(app, config_manager, root_dir, logger, get_state_manager)

    from .routes_chat import init_chat_routes
    init_chat_routes(app, config_manager, root_dir, logger)
    
    from .routes_auth import init_auth_routes
    init_auth_routes(app, config_manager, logger)
    
    from .routes_mcp import init_mcp_routes
    init_mcp_routes(app, config_manager, logger)

    from .routes_widgets import init_widget_routes
    init_widget_routes(app, config_manager, logger)

    from .routes_home import init_home_routes
    init_home_routes(app, config_manager, logger)

    from .routes_history import history_bp
    app.register_blueprint(history_bp)

    from .routes_remote_triggers import init_remote_trigger_routes
    init_remote_trigger_routes(app, logger, get_state_manager)

    # Media Player Extension Route Integration
    try:
        from hecos.plugins.media_player.routes import init_routes as init_media_player
        init_media_player(app)
        logger.info("[WebUI] Hecos Media Player plugin loaded.")
    except Exception as _mp_e:
        logger.warning(f"[WebUI] Media Player plugin could not load: {_mp_e}")

    # WEB_UI Shared Extensions
    try:
        from hecos.core.system.extension_loader import discover_webui_extensions, load_eager_extensions
        _webui_dir = os.path.dirname(__file__)
        discover_webui_extensions(_webui_dir)
        load_eager_extensions(app, "WEB_UI")
        logger.info("[WebUI] WEB_UI extensions loaded.")
    except Exception as _ext_e:
        logger.warning(f"[WebUI] WEB_UI extension discovery error: {_ext_e}")

    return app, debug_on
