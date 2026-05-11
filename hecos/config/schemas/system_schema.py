"""
MODULE: System Config Schema
DESCRIPTION: Pydantic v2 models for config/system.yaml
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field, field_validator


# ─── PRIVACY ──────────────────────────────────────────────────────────────────

class PrivacyConfig(BaseModel):
    default_mode: str = "normal"          # normal | auto_wipe | incognito
    auto_wipe_on_clear: bool = True       # wipe messages when session cleared
    wipe_messages: bool = True
    wipe_profile: bool = False
    wipe_context: bool = False



# ─── AI ───────────────────────────────────────────────────────────────────────

class AIConfig(BaseModel):
    model_config = ConfigDict(extra='ignore')
    active_personality: str = "Hecos_System_Soul.yaml"
    available_personalities: Dict[str, str] = {}
    save_special_instructions: bool = False
    special_instructions: str = ""
    enable_safety_instructions: bool = True
    safety_instructions: str = ""
    avatar_size: str = "medium" # small, medium, large




# ─── BACKEND ──────────────────────────────────────────────────────────────────

class CloudBackendConfig(BaseModel):
    model_config = ConfigDict(extra='ignore')
    model: str = "gemini/gemini-2.5-flash"
    temperature: float = 0.7


class KoboldBackendConfig(BaseModel):
    url: str = "http://localhost:5001"
    model: str = ""
    max_length: int = 512
    temperature: float = 0.8
    top_p: float = 0.92
    rep_pen: float = 1.1


class OllamaBackendConfig(BaseModel):
    model: str = "qwen2.5:1.5b"
    available_models: Dict[str, str] = {}
    num_ctx: int = 4096
    num_gpu: int = 25
    num_predict: int = 250
    temperature: float = 0.3
    top_p: float = 0.9
    repeat_penalty: float = 1.1
    keep_alive: str = "120m"


class BackendConfig(BaseModel):
    type: str = "cloud"
    cloud: CloudBackendConfig = Field(default_factory=CloudBackendConfig)
    kobold: KoboldBackendConfig = Field(default_factory=KoboldBackendConfig)
    ollama: OllamaBackendConfig = Field(default_factory=OllamaBackendConfig)


# ─── BRIDGE ───────────────────────────────────────────────────────────────────

class BridgeConfig(BaseModel):
    use_processor: bool = True
    chunk_delay_ms: int = 0
    debug_log: bool = True
    remove_think_tags: bool = True
    local_voice_enabled: bool = False
    webui_voice_enabled: bool = True
    webui_voice_stt: bool = True
    enable_tools: bool = True


# ─── COGNITION ────────────────────────────────────────────────────────────────

class CognitionConfig(BaseModel):
    memory_enabled: bool = True
    episodic_memory: bool = True
    clear_on_restart: bool = False
    include_identity_context: bool = True
    include_self_awareness: bool = True
    max_history_messages: int = 20


# ─── FILTERS ──────────────────────────────────────────────────────────────────

class CustomFilterObj(BaseModel):
    find: str
    replace: str = ""
    target: str = "both" # voice, text, both

class FiltersConfig(BaseModel):
    remove_asterisks: str = "both"  # "none", "voice", "text", "both"
    remove_round_brackets: str = "voice"
    remove_square_brackets: str = "none"
    custom_filters: List[CustomFilterObj] = Field(default_factory=list)
    custom_replacements: Dict[str, str] = {} # Keep for legacy compatibility if needed

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        # Apply pre-validation for backward compatibility
        from pydantic_core import core_schema
        schema = handler(source_type)
        return core_schema.no_info_before_validator_function(cls._migrate_legacy_bools, schema)

    @staticmethod
    def _migrate_legacy_bools(values: Any) -> Any:
        if not isinstance(values, dict):
            return values
        # Convert True -> "both" or "voice" based on old default behavior
        # In early models, asterisks/round were True for voice. 
        # But we just made them apply to both in the earlier fix! So True -> both.
        # Actually, let's map True to "both" and False to "none"
        for key in ["remove_asterisks", "remove_round_brackets", "remove_square_brackets"]:
            val = values.get(key)
            if isinstance(val, bool):
                values[key] = "both" if val else "none"
        return values


# ─── LLM ──────────────────────────────────────────────────────────────────────

class ProviderConfig(BaseModel):
    api_key: str = ""
    models: List[str] = []


class LLMConfig(BaseModel):
    model_config = ConfigDict(extra='ignore')
    allow_cloud: bool = True
    debug_llm: bool = True
    providers: Dict[str, ProviderConfig] = Field(default_factory=lambda: {
        "gemini": ProviderConfig(models=["gemini/gemini-2.0-flash"]),
        "openai": ProviderConfig(models=["openai/gpt-4o"]),
        "anthropic": ProviderConfig(models=["anthropic/claude-3-5-sonnet-20240620"]),
        "groq": ProviderConfig(models=["groq/llama-3.3-70b-versatile"]),
    })


# ─── LOGGING ──────────────────────────────────────────────────────────────────

class LoggingConfig(BaseModel):
    level: str = "DEBUG"
    destination: str = "console"
    message_types: str = "both"
    web_level: str = "BOTH"
    web_max_history: int = 100
    web_autoscroll: bool = True
    web_split: bool = False


# ─── MONITOR ──────────────────────────────────────────────────────────────────

class MonitorConfig(BaseModel):
    check_interval: int = 1
    restart_delay: int = 2


# ─── PLUGINS ──────────────────────────────────────────────────────────────────

class PluginDashboard(BaseModel):
    enabled: bool = True
    lazy_load: bool = False
    backend_timeout: float = 0.5
    monitor_interval: int = 2
    webui_dashboard_enabled: bool = True
    webui_telemetry_enabled: bool = True
    console_dashboard_enabled: bool = True
    console_telemetry_enabled: bool = True
    track_cpu: bool = True
    track_ram: bool = True
    track_vram: bool = True

    track_vram: bool = True

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
    lazy_load: bool = False # System usually stays eager as it provides core tools
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
    lazy_load: bool = False # Web UI must be eager to start the server
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
    lazy_load: bool = True
    reminder_mode: str = "voice"
    ringtone_path: str = "Default_System_Alert.mp3"
    time_format: str = "24h"
    max_reminders: int = 50
    snooze_default_minutes: int = 15
    reminder_snooze_ui: bool = False

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
    lazy_load: bool = True

class PluginUser(BaseModel):
    enabled: bool = True
    lazy_load: bool = True


# ─── EXTENSIONS ───────────────────────────────────────────────────────────────

class CalendarExtensionConfig(BaseModel):
    model_config = ConfigDict(extra='allow')
    calendar_locale: str = "en"
    calendar_country: str = "US"
    day_colors: List[str] = Field(default_factory=lambda: [""] * 7)
    calendar_sync_urls: List[str] = Field(default_factory=list)

    @field_validator('day_colors', mode='before')
    @classmethod
    def validate_day_colors(cls, v):
        if isinstance(v, dict):
            # Convert dictionary like {'0': '...', '1': '...'} to list
            try:
                sorted_keys = sorted(v.keys(), key=lambda x: int(x))
                return [v[k] for k in sorted_keys]
            except (ValueError, TypeError):
                return list(v.values())
        return v

class ExtensionsConfig(BaseModel):
    model_config = ConfigDict(extra='allow')
    calendar: CalendarExtensionConfig = Field(default_factory=CalendarExtensionConfig)

class MCPServerConfig(BaseModel):
    command: str
    args: List[str] = []
    env: Dict[str, str] = {}
    enabled: bool = True

class PluginMCPBridge(BaseModel):
    enabled: bool = False
    lazy_load: bool = False
    servers: Dict[str, MCPServerConfig] = Field(default_factory=dict)

class PluginsConfig(BaseModel):
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
    USER: PluginUser = Field(default_factory=PluginUser)
    extra_dirs: List[str] = []


# ─── PROCESSOR & ROUTING & SYSTEM ─────────────────────────────────────────────

class ProcessorConfig(BaseModel):
    debug_mode: bool = False
    log_level: str = "INFO"

class RoutingEngineConfig(BaseModel):
    mode: str = "auto"
    legacy_models: str = ""

class SystemFlagsConfig(BaseModel):
    fast_boot: bool = True
    flask_debug: bool = False


# ─── ROOT ─────────────────────────────────────────────────────────────────────

class SystemConfig(BaseModel):
    model_config = ConfigDict(extra='allow')
    """Root schema for config/system.yaml"""
    ai: AIConfig = Field(default_factory=AIConfig)
    backend: BackendConfig = Field(default_factory=BackendConfig)
    bridge: BridgeConfig = Field(default_factory=BridgeConfig)
    cognition: CognitionConfig = Field(default_factory=CognitionConfig)
    extensions: ExtensionsConfig = Field(default_factory=ExtensionsConfig)
    filters: FiltersConfig = Field(default_factory=FiltersConfig)
    language: str = "en"
    llm: LLMConfig = Field(default_factory=LLMConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    monitor: MonitorConfig = Field(default_factory=MonitorConfig)
    plugins: PluginsConfig = Field(default_factory=PluginsConfig)
    privacy: PrivacyConfig = Field(default_factory=lambda: PrivacyConfig())
    processor: ProcessorConfig = Field(default_factory=ProcessorConfig)
    routing_engine: RoutingEngineConfig = Field(default_factory=RoutingEngineConfig)
    system: SystemFlagsConfig = Field(default_factory=SystemFlagsConfig)
