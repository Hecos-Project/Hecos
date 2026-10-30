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
    important_paths: Dict[str, str] = {}


# PluginDrive removed — Drive is now an HPM system_app (type='app').
# It manages its own config independently and is NOT part of plugins.yaml.







# PluginFlows removed — Flows is now an HPM system_app (type='app').
# It manages its own config independently in config/data/flows.toml.

class PluginAutomation(BaseModel):
    model_config = ConfigDict(extra='allow')
    enabled: bool = True
    move_duration: float = 0.15
    type_interval: float = 0.02
    allow_window_control: bool = True


class PluginBrowserSearchTor(BaseModel):
    model_config = ConfigDict(extra='allow')
    enabled: bool = False
    socks_port: int = 9055
    control_port: int = 9056
    use_system_tor_if_available: bool = True
    auto_start: bool = True
    custom_proxy_url: str = ""


class PluginBrowserSearchSearxng(BaseModel):
    model_config = ConfigDict(extra='allow')
    enabled: bool = False
    url: str = "http://localhost:8080"
    custom_engines: str = ""


class PluginBrowserSearch(BaseModel):
    model_config = ConfigDict(extra='allow')
    enabled: bool = True
    default_mode: str = "clear"
    default_limit: int = 15
    safe_search: bool = False
    auto_fallback_tor: bool = True
    tor: PluginBrowserSearchTor = Field(default_factory=PluginBrowserSearchTor)
    searxng: PluginBrowserSearchSearxng = Field(default_factory=PluginBrowserSearchSearxng)
    engines: Dict[str, bool] = Field(default_factory=dict)
    max_concurrent_engines: int = 6
    request_timeout_sec: float = 12.0


class PluginBrowser(BaseModel):
    model_config = ConfigDict(extra='allow')
    enabled: bool = True
    lazy_load: bool = True
    headless: bool = False
    block_ads: bool = True
    startup_url: str = "http://localhost:7070"
    browser_type: str = "chromium"
    browser_engine_mode: str = "cdp_mode"
    cdp_port: int = 9222
    thread_timeout: float = 60.0
    nav_timeout: float = 30.0
    wait_timeout: float = 8.0
    action_timeout: float = 5.0
    search: PluginBrowserSearch = Field(default_factory=PluginBrowserSearch)


# ─── PLUGINS COLLECTION ───────────────────────────────────────────────────────

class PluginsConfig(BaseModel):
    model_config = ConfigDict(extra='allow')
    DASHBOARD: PluginDashboard = Field(default_factory=PluginDashboard)
    HELP: PluginHelp = Field(default_factory=PluginHelp)
    SYSTEM: PluginSystem = Field(default_factory=PluginSystem)
    WEB_UI: PluginWebUI = Field(default_factory=PluginWebUI)
    EXECUTOR: PluginExecutor = Field(default_factory=PluginExecutor)
    BROWSER: Optional[PluginBrowser] = Field(default_factory=PluginBrowser)
    AUTOMATION: Optional[PluginAutomation] = Field(default_factory=PluginAutomation)
    extra_dirs: List[str] = []


# ─── EXTENSIONS ───────────────────────────────────────────────────────────────

class ExtensionsConfig(BaseModel):
    model_config = ConfigDict(extra='allow')


# ─── ROOT SCHEMA FOR plugins.yaml ─────────────────────────────────────────────

class PluginsFileConfig(BaseModel):
    """Root schema for config/plugins.yaml"""
    model_config = ConfigDict(extra='allow')
    plugins: PluginsConfig = Field(default_factory=PluginsConfig)
    extensions: ExtensionsConfig = Field(default_factory=ExtensionsConfig)

