"""
MODULE: Config Schemas Package
DESCRIPTION: Pydantic v2 schemas for the Hecos layered config system.

File → Schema mapping:
  config/data/system.yaml  → SystemConfig      (system_schema.py)
  config/data/plugins.yaml → PluginsFileConfig  (plugins_schema.py)
  config/data/widgets.yaml → WidgetsFileConfig  (widgets_schema.py)
  config/data/agent.yaml   → AgentConfig        (agent_schema.py)
  config/data/audio.yaml   → AudioConfig        (audio_schema.py)
  config/data/media.yaml   → MediaConfig        (media_schema.py)
"""

from .system_schema import SystemConfig
from .plugins_schema import (
    PluginsFileConfig, PluginsConfig, ExtensionsConfig,
    PluginDashboard, PluginFileManager, PluginHelp, PluginImageGen,
    PluginMediaPlayer, PluginSystem, PluginSysNet, PluginWeb, PluginWebcam,
    PluginWebUI, PluginExecutor, PluginDrive, PluginRemoteTriggers,
    PluginReminder, PluginMCPBridge, PluginAutomation, PluginBrowser,
    PluginCalendar, PluginUsers, PluginDomotica,
    CalendarExtensionConfig, MCPServerConfig,
)
from .widgets_schema import WidgetsFileConfig, WidgetsConfig, WidgetPersistence
from .agent_schema import AgentConfig

__all__ = [
    "SystemConfig",
    "PluginsFileConfig", "PluginsConfig", "ExtensionsConfig",
    "PluginDashboard", "PluginFileManager", "PluginHelp", "PluginImageGen",
    "PluginMediaPlayer", "PluginSystem", "PluginSysNet", "PluginWeb",
    "PluginWebcam", "PluginWebUI", "PluginExecutor", "PluginDrive",
    "PluginRemoteTriggers", "PluginReminder", "PluginMCPBridge",
    "PluginAutomation", "PluginBrowser", "PluginCalendar", "PluginUsers",
    "PluginDomotica", "CalendarExtensionConfig", "MCPServerConfig",
    "WidgetsFileConfig", "WidgetsConfig", "WidgetPersistence",
    "AgentConfig",
]
