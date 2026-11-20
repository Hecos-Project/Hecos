"""
Hecos Web UI - Audio Configuration and Routing Facade
Coordinates sub-routers for audio controls, configuration/filters, and TTS engines/daemons.
"""

from .routes_audio_controls import register_audio_controls_routes
from .routes_audio_settings import register_audio_settings_routes
from .routes_audio_engines import register_audio_engines_routes


def init_audio_config_routes(app, cfg_mgr, root_dir, logger, get_sm=None):
    """
    Initializes all audio configuration and device control endpoints on the central Flask app.
    100% backward compatible with routes_audio.py.
    """
    # 1. Device toggles, speaking states, PTT, playback stop, and history
    register_audio_controls_routes(app, cfg_mgr, root_dir, logger, get_sm)

    # 2. Audio config, active engine parameters, regex filters, voices list, and cache stats
    register_audio_settings_routes(app, cfg_mgr, root_dir, logger, get_sm)

    # 3. TTS engines on-demand installer, diagnostic badges, Fish daemon controls, and models
    register_audio_engines_routes(app, cfg_mgr, root_dir, logger, get_sm)
