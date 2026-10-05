import os
from flask import send_from_directory, request, jsonify
from hecos.core.logging import logger

def init_routes(app, root_dir: str = None):
    logger.info("[DCC] Initializing routes...")
    
    _static_dir = os.path.join(os.path.dirname(__file__), "static")
    @app.route("/ext/dcc/static/<path:filename>")
    def dcc_static(filename):
        return send_from_directory(_static_dir, filename)

    # We will add config and capability routes later
