"""
hecos/core/ipc/__init__.py
─────────────────────────────────────────────────────────────────────────────
Hecos IPC Layer — Subprocess isolation for HPM plugins.
─────────────────────────────────────────────────────────────────────────────
"""
from .proxy import ModuleProxy
from .protocol import make_call, make_info, make_shutdown, parse_response

__all__ = ["ModuleProxy", "make_call", "make_info", "make_shutdown", "parse_response"]
