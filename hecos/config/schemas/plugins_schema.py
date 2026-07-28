"""
MODULE: Plugins & Extensions Config Schema
DESCRIPTION: Pydantic v2 models for config/plugins.yaml
             Contains all plugin configurations (CORE + PLUGIN + EXT)
             and the extensions block for advanced plugin settings.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


# ─── PLUGIN CLASSES ───────────────────────────────────────────────────────────

class PluginDashboard(BaseModel):
    enabled: bool = True
    lazy_load: bool = False
    console_telemetry_enabled: bool = True
    console_telemetry_cpu: bool = False
    console_telemetry_ram: bool = False
    console_telemetry_vram: bool = False





class PluginHelp(BaseModel):
    enabled: bool = True
    lazy_load: bool = True
    show_disabled: bool = False



class PluginSystem(BaseModel):
    enabled: bool = True
    lazy_load: bool = False
    enable_config_set: bool = True
    shell_command_timeout: int = 15
    shell_command_whitelist: List[str] = []
    explorer_mappings: Dict[str, str] = {}
    programs: Dict[str, str] = {}


class PluginSysNet(BaseModel):
    enabled: bool = True
    lazy_load: bool = True
    proxy_enabled: bool = False
    proxy_url: str = "socks5://localhost:9150"



class PluginWebUI(BaseModel):
    enabled: bool = True
    lazy_load: bool = False
    port: int = 7070
    api_port: int = 5000
    auto_open_browser: bool = False
    https_enabled: bool = False
    force_login: bool = True
    cert_file: str = "certs/cert.pem"
    key_file: str = "certs/key.pem"


class PluginExecutor(BaseModel):
    enabled: bool = True
    lazy_load: bool = True
    timeout_seconds: int = 10
    enable_shell_commands: bool = True
    shell_timeout: int = 15
    max_read_lines: int = 200
    workspace_dir: str = "workspace/sandbox"


# PluginDrive removed — Drive is now an HPM system_app (type='app').
# It manages its own config independently and is NOT part of plugins.yaml.







# PluginFlows removed — Flows is now an HPM system_app (type='app').
# It manages its own config independently in config/data/flows.toml.

# ─── PLUGINS COLLECTION ───────────────────────────────────────────────────────

class PluginsConfig(BaseModel):
    model_config = ConfigDict(extra='ignore')  # HPM package keys are NO LONGER stored here (they use their own .toml files)
    DASHBOARD: PluginDashboard = Field(default_factory=PluginDashboard)
    HELP: PluginHelp = Field(default_factory=PluginHelp)
    SYSTEM: PluginSystem = Field(default_factory=PluginSystem)
    SYS_NET: PluginSysNet = Field(default_factory=PluginSysNet)
    WEB_UI: PluginWebUI = Field(default_factory=PluginWebUI)
    EXECUTOR: PluginExecutor = Field(default_factory=PluginExecutor)
    # DRIVE removed — it is now an HPM system_app package
    # USERS removed — it is now an HPM package
    # FLOWS removed — it is now an HPM system_app package
    extra_dirs: List[str] = []


# ─── EXTENSIONS ───────────────────────────────────────────────────────────────

class ExtensionsConfig(BaseModel):
    model_config = ConfigDict(extra='allow')


# ─── ROOT SCHEMA FOR plugins.yaml ─────────────────────────────────────────────

class PluginsFileConfig(BaseModel):
    """Root schema for config/plugins.yaml"""
    model_config = ConfigDict(extra='ignore')
    plugins: PluginsConfig = Field(default_factory=PluginsConfig)
    extensions: ExtensionsConfig = Field(default_factory=ExtensionsConfig)
