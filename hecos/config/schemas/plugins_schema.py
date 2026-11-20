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


DEFAULT_EXECUTOR_ANTI_HALLUCINATION_DIRECTIVE = (
    "CRITICAL EXECUTOR ANTI-HALLUCINATION DIRECTIVE:\n"
    "1. NEVER claim, imply, or announce that files or apps were created, edited, fixed, verified, "
    "or started unless you ACTUALLY called an EXECUTOR tool (`EXECUTOR__read_file`, `EXECUTOR__run_aider_task`, "
    "`EXECUTOR__patch_file`, `EXECUTOR__write_file`, `EXECUTOR__start_app`, `EXECUTOR__run_project_test`) "
    "and observed its real output in this turn.\n"
    "2. When asked to inspect, fix, or build a project, DO NOT paste full updated files in chat claiming "
    "the fix is applied: invoke `EXECUTOR__read_file` first or `EXECUTOR__run_aider_task` / "
    "`EXECUTOR__patch_file` directly on disk, then verify with `EXECUTOR__start_app` or "
    "`EXECUTOR__run_project_test`.\n"
    "3. If your model is in text-only tool mode, emit explicit `EXECUTOR__tool_name(arg=\"...\")` calls "
    "and always use forward slashes `/` in Windows paths (e.g. `C:/Hecos/hecos/media/workspace/...`).\n"
    "4. Execute step by step: write 1-2 concise files per turn via `EXECUTOR__write_file` (or delegate multi-file generation to `EXECUTOR__run_aider_task`) and wait for disk confirmation BEFORE calling `check_syntax`, `run_project_test`, `start_app`, or `probe_url`."
)


class PluginExecutor(BaseModel):
    enabled: bool = True
    lazy_load: bool = False  # EXECUTOR is eager: must be callable via function-calling from turn-1
    timeout_seconds: int = 10
    enable_shell_commands: bool = True
    shell_timeout: int = 15
    max_read_lines: int = 200
    workspace_dir: str = "media/sandbox"
    important_paths: Dict[str, str] = {}
    coding_enabled: bool = False
    auto_verify_syntax_on_write: bool = True
    auto_run_existing_tests_on_write: bool = True
    auto_generate_unit_tests: bool = False
    default_run_timeout_seconds: int = 30
    allow_ui_script_execution: bool = True
    aider_enabled: bool = True
    aider_global_preset: str = "hecos_coder"
    aider_model: str = ""
    aider_num_ctx: int = 0
    aider_edit_format: str = ""
    aider_auto_lint: bool = True
    enable_anti_hallucination_guard: bool = True
    anti_hallucination_directive: str = DEFAULT_EXECUTOR_ANTI_HALLUCINATION_DIRECTIVE
    model_directive_override: str = ""


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

class PluginActionPlans(BaseModel):
    model_config = ConfigDict(extra='allow')
    enabled: bool = True
    lazy_load: bool = False
    llm_callable: bool = True
    plan_mode: str = "auto"
    auto_plan_min_steps_hint: int = 3
    expose_tools_in_custom_presets: bool = True
    checkpoint_enabled: bool = True
    resume_banner_enabled: bool = True
    resume_extra_steps: int = 10
    retention_days: int = 14
    flows_checkpoint_enabled: bool = True
    approval_timeout_seconds: int = 300


class PluginsConfig(BaseModel):
    model_config = ConfigDict(extra='allow')
    DASHBOARD: PluginDashboard = Field(default_factory=PluginDashboard)
    HELP: PluginHelp = Field(default_factory=PluginHelp)
    SYSTEM: PluginSystem = Field(default_factory=PluginSystem)
    WEB_UI: PluginWebUI = Field(default_factory=PluginWebUI)
    EXECUTOR: PluginExecutor = Field(default_factory=PluginExecutor)
    ACTION_PLANS: PluginActionPlans = Field(default_factory=PluginActionPlans)
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

