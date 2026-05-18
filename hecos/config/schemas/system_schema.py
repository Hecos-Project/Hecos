"""
MODULE: System Config Schema
DESCRIPTION: Pydantic v2 models for config/system.yaml (core system only).
             Plugins, extensions and widgets have their own schema files:
               - plugins_schema.py  → config/plugins.yaml
               - widgets_schema.py  → config/widgets.yaml
"""

from __future__ import annotations
from typing import Any, Dict, List
from pydantic import BaseModel, ConfigDict, Field, field_validator


# ─── PRIVACY ──────────────────────────────────────────────────────────────────

class PrivacyConfig(BaseModel):
    default_mode: str = "normal"
    auto_wipe_on_clear: bool = True
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
    avatar_size: str = "medium"


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
    target: str = "both"


class FiltersConfig(BaseModel):
    remove_asterisks: str = "both"
    remove_round_brackets: str = "voice"
    remove_square_brackets: str = "none"
    custom_filters: List[CustomFilterObj] = Field(default_factory=list)
    custom_replacements: Dict[str, str] = {}

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        from pydantic_core import core_schema
        schema = handler(source_type)
        return core_schema.no_info_before_validator_function(cls._migrate_legacy_bools, schema)

    @staticmethod
    def _migrate_legacy_bools(values: Any) -> Any:
        if not isinstance(values, dict):
            return values
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


# ─── PROCESSOR & ROUTING & SYSTEM FLAGS ───────────────────────────────────────

class ProcessorConfig(BaseModel):
    debug_mode: bool = False
    log_level: str = "INFO"


class RoutingEngineConfig(BaseModel):
    mode: str = "auto"
    legacy_models: str = ""


class SystemFlagsConfig(BaseModel):
    fast_boot: bool = True
    flask_debug: bool = False


# ─── AGENT (inline in system.yaml for legacy compatibility) ───────────────────
# NOTE: The canonical agent config lives in agent.yaml (AgentConfig schema).
# This block is kept in SystemConfig only to absorb the `agent:` key that
# some old system.yaml files still carry, preventing Pydantic validation errors.
# On save, the `agent:` key is NOT written back to system.yaml.

class AgentInlineConfig(BaseModel):
    model_config = ConfigDict(extra='ignore')
    enabled: bool = True
    max_iterations: int = 12
    verbose_traces: bool = True
    action_console_enabled: bool = True


# ─── ROOT ─────────────────────────────────────────────────────────────────────

class SystemConfig(BaseModel):
    """Root schema for config/system.yaml (core system keys only).
    plugins, extensions and widgets are NOT part of this schema —
    they live in plugins.yaml (PluginsFileConfig) and widgets.yaml (WidgetsFileConfig).
    """
    model_config = ConfigDict(extra='ignore')
    ai: AIConfig = Field(default_factory=AIConfig)
    backend: BackendConfig = Field(default_factory=BackendConfig)
    bridge: BridgeConfig = Field(default_factory=BridgeConfig)
    cognition: CognitionConfig = Field(default_factory=CognitionConfig)
    filters: FiltersConfig = Field(default_factory=FiltersConfig)
    language: str = "en"
    llm: LLMConfig = Field(default_factory=LLMConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    monitor: MonitorConfig = Field(default_factory=MonitorConfig)
    privacy: PrivacyConfig = Field(default_factory=PrivacyConfig)
    processor: ProcessorConfig = Field(default_factory=ProcessorConfig)
    routing_engine: RoutingEngineConfig = Field(default_factory=RoutingEngineConfig)
    system: SystemFlagsConfig = Field(default_factory=SystemFlagsConfig)
    # Absorb legacy `agent:` key from old system.yaml — NOT re-serialized on save
    agent: AgentInlineConfig = Field(default_factory=AgentInlineConfig)
