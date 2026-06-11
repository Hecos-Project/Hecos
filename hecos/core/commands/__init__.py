"""
Hecos Direct Command System (HDCS)
Core package for slash command registration, discovery, and execution.

Usage:
    from hecos.core.commands import get_registry, execute_command
"""

from .registry import CommandRegistry, get_registry
from .executor import CommandExecutor

__all__ = ["CommandRegistry", "get_registry", "CommandExecutor"]
