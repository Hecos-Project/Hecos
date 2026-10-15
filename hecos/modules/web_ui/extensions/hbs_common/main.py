import os
from flask import send_from_directory
from hecos.core.logging import logger

def init_routes(app, root_dir: str = None):
    logger.info("[HBS Common] Registering static routes...")
    _static_dir = os.path.join(os.path.dirname(__file__), "static")
    
    @app.route("/ext/hbs_common/static/<path:filename>")
    def hbs_common_static(filename):
        return send_from_directory(_static_dir, filename)
