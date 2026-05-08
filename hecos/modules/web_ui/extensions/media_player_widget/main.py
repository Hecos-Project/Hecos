"""
Media Player Widget — WEB_UI Sidebar Extension
Registers the static assets route for the media player mini widget.
No separate API needed — reuses /api/media_player/* endpoints from the main plugin.
"""
import os
from hecos.core.logging import logger


def init_routes(app, root_dir: str = None):
    from flask import send_from_directory

    _static_dir = os.path.join(os.path.dirname(__file__), "static")

    if os.path.isdir(_static_dir):
        @app.route("/ext/media_player_widget/static/<path:filename>")
        def media_player_widget_static(filename):
            return send_from_directory(_static_dir, filename)

    logger.debug("MediaPlayerWidget", "Media Player sidebar widget loaded.")
