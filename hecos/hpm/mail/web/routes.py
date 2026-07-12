from hecos.hpm.mail.api import mail_bp

def init_plugin_routes(app, cfg_mgr, root_dir, logger, get_sm=None):
    if "mail" not in app.blueprints:
        app.register_blueprint(mail_bp)
        logger.info("[MAIL] API blueprint registered at /api/mail via HPM loader")
