"""
MODULE: System Config Schema
DESCRIPTION: Pydantic v2 models for config/system.yaml
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# â”€â”€â”€ AI â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class AIConfig(BaseModel):
    active_personality: str = "Hecos_System_Soul.txt"
    available_personalities: Dict[str, str] = {}
    save_special_instructions: bool = False
    special_instructions: str = ""


# â”€â”€â”€ BACKEND â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class CloudBackendConfig(BaseModel):
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


# â”€â”€â”€ BRIDGE â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class BridgeConfig(BaseModel):
    use_processor: bool = True
    chunk_delay_ms: int = 0
    debug_log: bool = True
    remove_think_tags: bool = True
    local_voice_enabled: bool = False
    webui_voice_enabled: bool = True
    webui_voice_stt: bool = True
    enable_tools: bool = True


# â”€â”€â”€ COGNITION â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class CognitionConfig(BaseModel):
    memory_enabled: bool = True
    episodic_memory: bool = True
    clear_on_restart: bool = False
    include_identity_context: bool = True
    include_self_awareness: bool = True
    max_history_messages: int = 20


# â”€â”€â”€ FILTERS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class FiltersConfig(BaseModel):
    remove_asterisks: bool = True
    remove_round_brackets: bool = True
    remove_square_brackets: bool = False
    custom_replacements: Dict[str, str] = {}


# â”€â”€â”€ LLM â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class ProviderConfig(BaseModel):
    api_key: str = ""
    models: List[str] = []


class LLMConfig(BaseModel):
    allow_cloud: bool = True
    debug_llm: bool = True
    providers: Dict[str, ProviderConfig] = Field(default_factory=lambda: {
        "gemini": ProviderConfig(models=["gemini/gemini-2.0-flash"]),
        "openai": ProviderConfig(models=["openai/gpt-4o"]),
        "anthropic": ProviderConfig(models=["anthropic/claude-3-5-sonnet-20240620"]),
        "groq": ProviderConfig(models=["groq/llama-3.3-70b-versatile"]),
    })


# â”€â”€â”€ LOGGING â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class LoggingConfig(BaseModel):
    level: str = "DEBUG"
    destination: str = "console"
    message_types: str = "both"
    web_level: str = "BOTH"
    web_max_history: int = 100
    web_autoscroll: bool = True
    web_split: bool = False


# â”€â”€â”€ MONITOR â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class MonitorConfig(BaseModel):
    check_interval: int = 1
    restart_delay: int = 2


# â”€â”€â”€ PLUGINS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class PluginDashboard(BaseModel):
    enabled: bool = True
    lazy_load: bool = False
    backend_timeout: float = 0.5
    monitor_interval: int = 2

class PluginFileManager(BaseModel):
    enabled: bool = True
    lazy_load: bool = False
    enable_path_mapping: bool = True
    max_list_items: int = 5
    max_read_lines: int = 50

class PluginHelp(BaseModel):
    enabled: bool = True
    lazy_load: bool = False
    show_disabled: bool = False

class PluginImageGen(BaseModel):
    enabled: bool = True
    lazy_load: bool = False
    width: int = 1024
    height: int = 1024
    nologo: bool = False

class PluginMedia(BaseModel):
    enabled: bool = True
    lazy_load: bool = False

class PluginRoleplay(BaseModel):
    enabled: bool = True
    lazy_load: bool = False
    default_character: str = ""
    default_scene: str = ""
    llm_model: str = ""
    characters_dir: str = "plugins/roleplay/characters"
    scenes_dir: str = "plugins/roleplay/scenes"

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
    lazy_load: bool = False
    proxy_url: str = "socks5://localhost:9150"

class PluginWeb(BaseModel):
    enabled: bool = True
    lazy_load: bool = False
    llm_model: str = ""
    search_engine: str = "google"
    use_https: bool = True
    open_in_new_tab: bool = False

class PluginWebcam(BaseModel):
    enabled: bool = True
    lazy_load: bool = False
    camera_index: int = 0
    image_format: str = "jpg"
    save_directory: str = "snapshots"
    stabilization_delay: float = 0.5

class PluginWebUI(BaseModel):
    enabled: bool = True
    lazy_load: bool = False
    port: int = 7070
    auto_open_browser: bool = False
    https_enabled: bool = False
    cert_file: str = "certs/cert.pem"
    key_file: str = "certs/key.pem"

class PluginExecutor(BaseModel):
    enabled: bool = True
    lazy_load: bool = False
    timeout_seconds: int = 10

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

class PluginsConfig(BaseModel):
    DASHBOARD: PluginDashboard = Field(default_factory=PluginDashboard)
    FILE_MANAGER: PluginFileManager = Field(default_factory=PluginFileManager)
    HELP: PluginHelp = Field(default_factory=PluginHelp)
    IMAGE_GEN: PluginImageGen = Field(default_factory=PluginImageGen)
    MEDIA: PluginMedia = Field(default_factory=PluginMedia)
    ROLEPLAY: PluginRoleplay = Field(default_factory=PluginRoleplay)
    SYSTEM: PluginSystem = Field(default_factory=PluginSystem)
    SYS_NET: PluginSysNet = Field(default_factory=PluginSysNet)
    WEB: PluginWeb = Field(default_factory=PluginWeb)
    WEBCAM: PluginWebcam = Field(default_factory=PluginWebcam)
    WEB_UI: PluginWebUI = Field(default_factory=PluginWebUI)
    EXECUTOR: PluginExecutor = Field(default_factory=PluginExecutor)
    DRIVE: PluginDrive = Field(default_factory=PluginDrive)
    extra_dirs: List[str] = []


# â”€â”€â”€ PROCESSOR & ROUTING & SYSTEM â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class ProcessorConfig(BaseModel):
    debug_mode: bool = False
    log_level: str = "INFO"

class RoutingEngineConfig(BaseModel):
    mode: str = "auto"
    legacy_models: str = ""

class SystemFlagsConfig(BaseModel):
    fast_boot: bool = True
    flask_debug: bool = False


# â”€â”€â”€ ROOT â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class SystemConfig(BaseModel):
    """Root schema for config/system.yaml"""
    ai: AIConfig = Field(default_factory=AIConfig)
    backend: BackendConfig = Field(default_factory=BackendConfig)
    bridge: BridgeConfig = Field(default_factory=BridgeConfig)
    cognition: CognitionConfig = Field(default_factory=CognitionConfig)
    filters: FiltersConfig = Field(default_factory=FiltersConfig)
    language: str = "en"
    llm: LLMConfig = Field(default_factory=LLMConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    monitor: MonitorConfig = Field(default_factory=MonitorConfig)
    plugins: PluginsConfig = Field(default_factory=PluginsConfig)
    processor: ProcessorConfig = Field(default_factory=ProcessorConfig)
    routing_engine: RoutingEngineConfig = Field(default_factory=RoutingEngineConfig)
    system: SystemFlagsConfig = Field(default_factory=SystemFlagsConfig)
