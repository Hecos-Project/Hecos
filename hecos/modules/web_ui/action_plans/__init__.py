"""
hecos/modules/web_ui/action_plans/__init__.py
WebUI subpackage exposing Action Plans, Flow checkpoints, and Hub configuration routes.
"""

from hecos.modules.web_ui.action_plans.routes import init_action_plans_routes

__all__ = ["init_action_plans_routes"]
