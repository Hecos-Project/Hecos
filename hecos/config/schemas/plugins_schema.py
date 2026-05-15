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
    backend_timeout: float = 0.5
    monitor_interval: int = 2
    webui_dashboard_enabled: bool = True
    webui_telemetry_enabled: bool = False
    console_dashboard_enabled: bool = True
    console_telemetry_enabled: bool = False
    track_cpu: bool = False
    track_ram: bool = False
    track_vram: bool = False


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


class PluginImageGen(BaseModel):
    enabled: bool = True
    lazy_load: bool = True
    width: int = 1024
    height: int = 1024
    nologo: bool = False


class PluginMediaPlayer(BaseModel):
    enabled: bool = True
    lazy_load: bool = True


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


class PluginWebcam(BaseModel):
    enabled: bool = True
    lazy_load: bool = True
    camera_index: int = 0
    image_format: str = "jpg"
    save_directory: str = "snapshots"
    stabilization_delay: float = 0.5


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


class PluginRemoteTriggers(BaseModel):
    enabled: bool = True
    lazy_load: bool = True
    settings: Dict[str, Any] = Field(default_factory=lambda: {
        "enable_mediasession": True,
        "enable_volume_keys": True,
        "enable_volume_loop": False,
        "feedback_sounds": True,
        "visual_indicator": True
    })


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


class PluginReminder(BaseModel):
    enabled: bool = True
    lazy_load: bool = False
    reminder_mode: str = "voice"
    ringtone_path: str = "Default_System_Alert.mp3"
    time_format: str = "24h"
    max_reminders: int = 50
    snooze_default_minutes: int = 15
    reminder_snooze_ui: bool = False


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


class PluginCalendar(BaseModel):
    enabled: bool = True
    lazy_load: bool = False


class PluginUsers(BaseModel):
    enabled: bool = True
    lazy_load: bool = True


class PluginDomotica(BaseModel):
    enabled: bool = False
    lazy_load: bool = True


# ─── PLUGINS COLLECTION ───────────────────────────────────────────────────────

class PluginsConfig(BaseModel):
    model_config = ConfigDict(extra='allow')
    DASHBOARD: PluginDashboard = Field(default_factory=PluginDashboard)
    FILE_MANAGER: PluginFileManager = Field(default_factory=PluginFileManager)
    HELP: PluginHelp = Field(default_factory=PluginHelp)
    IMAGE_GEN: PluginImageGen = Field(default_factory=PluginImageGen)
    MEDIA_PLAYER: PluginMediaPlayer = Field(default_factory=PluginMediaPlayer)
    SYSTEM: PluginSystem = Field(default_factory=PluginSystem)
    SYS_NET: PluginSysNet = Field(default_factory=PluginSysNet)
    WEB: PluginWeb = Field(default_factory=PluginWeb)
    WEBCAM: PluginWebcam = Field(default_factory=PluginWebcam)
    WEB_UI: PluginWebUI = Field(default_factory=PluginWebUI)
    EXECUTOR: PluginExecutor = Field(default_factory=PluginExecutor)
    DRIVE: PluginDrive = Field(default_factory=PluginDrive)
    REMOTE_TRIGGERS: PluginRemoteTriggers = Field(default_factory=PluginRemoteTriggers)
    REMINDER: PluginReminder = Field(default_factory=PluginReminder)
    MCP_BRIDGE: PluginMCPBridge = Field(default_factory=PluginMCPBridge)
    AUTOMATION: PluginAutomation = Field(default_factory=PluginAutomation)
    BROWSER: PluginBrowser = Field(default_factory=PluginBrowser)
    CALENDAR: PluginCalendar = Field(default_factory=PluginCalendar)
    USERS: PluginUsers = Field(default_factory=PluginUsers)
    DOMOTICA: PluginDomotica = Field(default_factory=PluginDomotica)
    extra_dirs: List[str] = []


# ─── EXTENSIONS ───────────────────────────────────────────────────────────────

class CalendarExtensionConfig(BaseModel):
    model_config = ConfigDict(extra='allow')
    calendar_locale: str = "en-US"
    calendar_country: str = "US"
    day_colors: List[str] = Field(default_factory=lambda: [""] * 7)
    calendar_sync_urls: List[str] = Field(default_factory=list)
    bg_color: str = ""
    bg_image: str = ""

    @field_validator('day_colors', mode='before')
    @classmethod
    def validate_day_colors(cls, v):
        if isinstance(v, dict):
            try:
                sorted_keys = sorted(v.keys(), key=lambda x: int(x))
                return [v[k] for k in sorted_keys]
            except (ValueError, TypeError):
                return list(v.values())
        return v


class ExtensionsConfig(BaseModel):
    model_config = ConfigDict(extra='allow')
    calendar: CalendarExtensionConfig = Field(default_factory=CalendarExtensionConfig)


# ─── ROOT SCHEMA FOR plugins.yaml ─────────────────────────────────────────────

class PluginsFileConfig(BaseModel):
    """Root schema for config/plugins.yaml"""
    model_config = ConfigDict(extra='ignore')
    plugins: PluginsConfig = Field(default_factory=PluginsConfig)
    extensions: ExtensionsConfig = Field(default_factory=ExtensionsConfig)
