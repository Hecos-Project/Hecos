import os
import json
import threading
import time
from flask import request, jsonify

def init_audio_routes(app, cfg_mgr, root_dir, logger, get_sm=None):
    from .routes_audio_stream import init_audio_stream_routes
    from .routes_audio_config import init_audio_config_routes

    # Delegate heavy audio streaming and IO
    init_audio_stream_routes(app, cfg_mgr, root_dir, logger, get_sm)

    # Delegate audio toggles and configuration state
    init_audio_config_routes(app, cfg_mgr, root_dir, logger, get_sm)
