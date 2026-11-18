"""
hecos/modules/web_ui/agent_resume/__init__.py
WebUI subpackage exposing crash/timeout agent resume routes.
"""

from hecos.modules.web_ui.agent_resume.routes import init_agent_resume_routes

__all__ = ["init_agent_resume_routes"]
