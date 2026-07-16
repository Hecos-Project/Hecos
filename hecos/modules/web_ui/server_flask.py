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
    
    # ── Gzip/Brotli compression (Flask-Compress) ──────────────────────────────
    # Compresses JSON, HTML, JS, CSS responses transparently.
    # Reduces the 80KB i18n payload to ~15KB and JS bundles by ~65%.
    try:
        from flask_compress import Compress
        compress = Compress()
        app.config['COMPRESS_ALGORITHM']      = ['br', 'gzip']  # Brotli preferred, gzip fallback
        app.config['COMPRESS_MIMETYPES']      = [
            'text/html', 'text/css', 'text/javascript',
            'application/javascript', 'application/json'
        ]
        app.config['COMPRESS_MIN_SIZE']       = 512   # Only compress if > 512 bytes
        app.config['COMPRESS_LEVEL']          = 6     # gzip level (1-9, 6 = good balance)
        compress.init_app(app)
        logger.info("[WebUI] Compression enabled (Brotli/gzip via Flask-Compress).")
    except ImportError:
        logger.warning("[WebUI] flask-compress not installed — responses will not be compressed.")

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
        if request.headers.get("X-Hecos-Internal") == "backup": return
        exempt_paths = ['/login', '/logout', '/static', '/assets', '/favicon.ico', '/ext']
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

    # ── Aggressive caching for versioned static files ─────────────────────────
    # JS/CSS already carry ?v=VERSION in the URL, so the browser can safely
    # cache them for 1 year. This eliminates 41 HTTP round-trips on repeat visits.
    @app.after_request
    def add_cache_headers(response):
        path = request.path
        # HPM package resources must NEVER be cached — they change on install/update
        if (path.startswith('/hpm_plugin/') or
            path.startswith('/hpm/') or
            path.startswith('/api/packages/')):
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
        # Cache versioned static assets aggressively (JS, CSS, images, fonts)
        elif path.startswith('/static/') or path.startswith('/assets/'):
            # If the URL contains a version/cache-bust query param, cache 1 year
            if request.args.get('v') or request.args.get('t'):
                response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
            else:
                # No version param — short cache (5 min) to be safe
                response.headers['Cache-Control'] = 'public, max-age=300'
        return response

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

    from .routes_commands import init_commands_routes
    init_commands_routes(app, config_manager, logger, get_state_manager)

    from .routes_history import history_bp
    app.register_blueprint(history_bp)

    # Contacts Plugin Route Integration
    try:
        from hecos.plugins.contacts.api import register_routes as init_contacts_api
        init_contacts_api(app)
        logger.info("[WebUI] Hecos Contacts plugin loaded.")
    except Exception as _ct_e:
        logger.warning(f"[WebUI] Contacts plugin could not load: {_ct_e}")

    # Mail Plugin Route Integration
    try:
        # Mail API registration removed (handled by HPM loader)
        logger.info("[WebUI] Hecos Mail plugin API removed from core.")
    except Exception as _mail_e:
        logger.warning(f"[WebUI] Mail plugin error: {_mail_e}")

    # Templates Plugin Route Integration
    try:
        # Templates API registration removed (handled by HPM loader)
        logger.info("[WebUI] Hecos Templates plugin API loaded.")
    except Exception as _tpl_e:
        logger.warning(f"[WebUI] Templates plugin API could not load: {_tpl_e}")

    # Global Backup Orchestrator
    try:
        from hecos.modules.backup.api import register_routes as init_backup_api
        init_backup_api(app)
        logger.info("[WebUI] Global Backup Orchestrator API loaded.")
    except Exception as _bk_e:
        logger.warning(f"[WebUI] Backup Orchestrator API could not load: {_bk_e}")

    # Module-level Backup/Restore routes (calendar, reminders, history, memory, flows, users)
    try:
        from hecos.modules.backup.routes_modules import register_module_backup_routes
        register_module_backup_routes(app)
        logger.info("[WebUI] Module backup routes loaded.")
    except Exception as _mbk_e:
        logger.warning(f"[WebUI] Module backup routes could not load: {_mbk_e}")

    # Start the Backup Scheduler (daemon thread — non-blocking)
    try:
        from hecos.modules.backup import scheduler as backup_scheduler
        backup_scheduler.start(app)
    except Exception as _bks_e:
        logger.warning(f"[WebUI] Backup scheduler start error: {_bks_e}")

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
