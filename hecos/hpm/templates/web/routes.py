from hecos.hpm.templates.api import templates_bp

def init_plugin_routes(app, cfg_mgr, root_dir, logger, get_sm=None):
    if "templates" not in app.blueprints:
        app.register_blueprint(templates_bp)
        logger.info("[TEMPLATES] API blueprint registered at /api/templates via HPM loader")
