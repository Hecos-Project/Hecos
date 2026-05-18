"""
Module B — Control Room Standalone
Flask route for /home — the full-screen widget dashboard.
Registered in server.py after all other routes.
"""
import logging

_log = logging.getLogger("HecosHomeRoute")


def init_home_routes(app, cfg_mgr, logger_ref=None):
    """Registers the /home standalone dashboard route."""
    _log_ref = logger_ref or _log

    @app.route("/home")
    def home_page():
        from flask import render_template, make_response
        from flask_login import current_user
        from hecos.core.system.extension_loader import get_sidebar_widgets
        from hecos.core.i18n.translator import get_translator

        try:
            cfg = cfg_mgr.config
            wui_cfg = cfg.get("plugins", {}).get("WEB_UI", {})

            if not wui_cfg.get("control_room_home", True):
                return "<h1>Control Room Disabled</h1><p>Standalone home page is disabled in Central Hub.</p>", 403

            translations = get_translator().get_translations()
            widgets = get_sidebar_widgets(config=cfg)

            resp = make_response(render_template(
                "home.html",
                current_user=current_user,
                zconfig=cfg,
                translations=translations,
                sidebar_widgets=widgets,
            ))
            resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            resp.headers["Pragma"] = "no-cache"
            return resp

        except Exception as exc:
            _log_ref.error(f"[Home] Error rendering /home: {exc}")
            return f"<h1>Control Room</h1><p>Error: {exc}</p>", 500
