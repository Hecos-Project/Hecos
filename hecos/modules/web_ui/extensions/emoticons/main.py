import os
from flask import send_from_directory

def init_routes(app, root_dir: str = None):
    _static_dir = os.path.join(os.path.dirname(__file__), "static")
    @app.route("/ext/emoticons/static/<path:filename>")
    def emoticons_static(filename):
        return send_from_directory(_static_dir, filename)
