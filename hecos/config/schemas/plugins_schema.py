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

# --- Dashboard removed ---


class PluginFileManager(BaseModel):
    enabled: bool = True
    lazy_load: bool = True
    enable_path_mapping: bool = True
    max_list_items: int = 5
    max_read_lines: int = 50


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


class PluginWeb(BaseModel):
    enabled: bool = True
    lazy_load: bool = True
    llm_model: str = ""
    search_engine: str = "google"
    use_https: bool = True
    open_in_new_tab: bool = False


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


class PluginDrive(BaseModel):
    enabled: bool = True
    lazy_load: bool = True
    root_dir: str = ""
    max_upload_mb: int = 100
    allowed_extensions: str = ""
    editor: Dict[str, Any] = Field(default_factory=lambda: {
        "enabled": True,
        "theme": "vs-dark",
        "max_file_size_kb": 1024,
        "word_wrap": True,
        "spell_check": False
    })



class MCPServerConfig(BaseModel):
    command: str
    args: List[str] = []
    env: Dict[str, str] = {}
    enabled: bool = True


class PluginMCPBridge(BaseModel):
    enabled: bool = False
    lazy_load: bool = False
    servers: Dict[str, MCPServerConfig] = Field(default_factory=dict)


class PluginAutomation(BaseModel):
    enabled: bool = True
    lazy_load: bool = True
    move_duration: float = 0.15
    type_interval: float = 0.02
    allow_window_control: bool = True


class PluginBrowser(BaseModel):
    enabled: bool = True
    lazy_load: bool = True
    headless: bool = False
    block_ads: bool = True
    startup_url: str = "http://localhost:7070"
    default_timeout: int = 10000
    browser_type: str = "chromium"
    browser_engine_mode: str = "app_mode"
    cdp_port: int = 9222



class PluginUsers(BaseModel):
    enabled: bool = True
    lazy_load: bool = True


class PluginContacts(BaseModel):
    enabled: bool = True
    lazy_load: bool = True


class PluginFlows(BaseModel):
    """Hecos Flows — visual orchestration engine."""
    enabled: bool = True
    lazy_load: bool = True
    # Path (relative to Hecos root) where flow YAML files are stored
    flows_dir: str = "workspace/flows"
    # Enable/disable APScheduler-based cron and interval triggers
    scheduler_enabled: bool = True
    # Timezone for APScheduler (e.g. 'Europe/Rome', 'local', 'UTC')
    scheduler_timezone: str = "local"
    # Log retention: max SSE log entries kept per run
    max_log_entries: int = 500
    # LLM temperature used by the NLP compiler (0–1)
    compiler_temperature: float = 0.1
    # Max tokens the NLP compiler may generate
    compiler_max_tokens: int = 2048
    # If true, auto-save compiled flows immediately without preview
    auto_save_compiled: bool = False
    # Enable Jinja2 rendering in YAML params (set False to disable for security)
    jinja2_rendering: bool = True
    # Max parallel flows that can run concurrently
    max_concurrent_runs: int = 5
    # Enable automatic background saving of the flow canvas
    autosave_enabled: bool = True
    # Interval in minutes for the background auto-save
    autosave_interval_minutes: int = 1


# ─── PLUGINS COLLECTION ───────────────────────────────────────────────────────

class PluginsConfig(BaseModel):
    model_config = ConfigDict(extra='ignore')  # HPM package keys are NOT stored here
    FILE_MANAGER: PluginFileManager = Field(default_factory=PluginFileManager)
    HELP: PluginHelp = Field(default_factory=PluginHelp)
    SYSTEM: PluginSystem = Field(default_factory=PluginSystem)
    SYS_NET: PluginSysNet = Field(default_factory=PluginSysNet)
    WEB: PluginWeb = Field(default_factory=PluginWeb)
    WEB_UI: PluginWebUI = Field(default_factory=PluginWebUI)
    EXECUTOR: PluginExecutor = Field(default_factory=PluginExecutor)
    DRIVE: PluginDrive = Field(default_factory=PluginDrive)
    MCP_BRIDGE: PluginMCPBridge = Field(default_factory=PluginMCPBridge)
    AUTOMATION: PluginAutomation = Field(default_factory=PluginAutomation)
    BROWSER: PluginBrowser = Field(default_factory=PluginBrowser)
    USERS: PluginUsers = Field(default_factory=PluginUsers)
    CONTACTS: PluginContacts = Field(default_factory=PluginContacts)

    FLOWS: PluginFlows = Field(default_factory=PluginFlows)
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
