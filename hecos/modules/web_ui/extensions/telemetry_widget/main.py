"""
Telemetry Widget — WEB_UI Sidebar Extension
A WebUI widget that displays backend system status, CPU/RAM telemetry, and audio statuses.
"""
from hecos.core.logging import logger

def init_routes(app, root_dir: str = None):
    # No custom API routes needed since the widget uses the global /hecos/status endpoint.
    logger.debug("TelemetryWidget", "Telemetry sidebar dashboard widget loaded.")
