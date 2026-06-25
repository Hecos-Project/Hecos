"""
package_schema.py
─────────────────────────────────────────────────────────────────────────────
Hecos Package Manager — hpkg_manifest.json Schema

Every .hpkg zip must contain an hpkg_manifest.json at its root that
conforms to this schema. Pydantic is used for validation so that error
messages are clear for third-party developers.

Package types:
  plugin      → installs into hecos/plugins/<id>/
  module      → installs into hecos/modules/<id>/
  theme       → installs CSS/assets only
  skill_pack  → installs additional HDCS slash-command packs
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


# ── Config Panel Descriptor ─────────────────────────────────────────────────

class ConfigPanelDescriptor(BaseModel):
    """Describes how to inject a configuration panel for this package."""

    tab_id: str = Field(..., description="Unique ID of the tab, e.g. 'my_plugin'")
    tab_label: str = Field(..., description="Human-readable label shown in the nav")
    tab_icon: str = Field("fa-cube", description="FontAwesome icon class, e.g. 'fa-envelope'")

    # Paths INSIDE the .hpkg zip (not absolute filesystem paths)
    template_file: str = Field(
        ...,
        description="Path inside the zip to the HTML fragment, e.g. 'web_ui/templates/config_myplugin.html'"
    )
    js_file: Optional[str] = Field(
        None,
        description="Path inside the zip to the JS file, e.g. 'web_ui/static/js/myplugin_panel.js'"
    )
    css_file: Optional[str] = Field(
        None,
        description="Optional path to a CSS file inside the zip"
    )
    
    category: Optional[str] = Field(
        "CONNETTIVITÀ",
        description="Category in the Config Hub (e.g. MULTIMEDIA, SISTEMA, CONNETTIVITÀ)"
    )
    
    api_routes_file: Optional[str] = Field(
        None,
        description="Path inside zip to a .py file exporting init_plugin_routes()"
    )
    
    config_api_get: Optional[str] = Field(None, description="GET endpoint for config JSON")
    config_api_post: Optional[str] = Field(None, description="POST endpoint for config JSON")

    class Config:
        extra = "allow"


# ── Widget Descriptor ───────────────────────────────────────────────────────

class WidgetDescriptor(BaseModel):
    """Describes a sidebar/control room widget bundled with this package."""

    id: str = Field(
        ...,
        description="Unique ID of the widget extension (e.g. 'webcam_widget')"
    )
    extension_path: str = Field(
        ...,
        description="Path inside zip to the extension directory, e.g. 'web_ui/extensions/my_widget/'"
    )


# ── Main Package Manifest ────────────────────────────────────────────────────

class HpkgManifest(BaseModel):
    """
    Root manifest schema for a .hpkg package.

    Example hpkg_manifest.toml:
    id = "mail"
        "name": "Hecos Mail",
        "version": "1.0.0",
        "hecos_min_version": "0.34.0",
        "type": "plugin",
        "author": "Hecos Team",
        "description": "Full-featured email plugin.",
        "target_dir": "plugins",
        "plugin_dir": "plugin/",
        "config_panel": { ... },
        "widgets": [],
    dependencies = []
    pip_requirements = ["imapclient>=2.3"]

    [config_panel]
    tab_id = "mail"
    tab_label = "Mail"
    tab_icon = "fa-envelope"
    template_file = "web_ui/templates/config_mail.html"
    js_file = "web_ui/static/js/mail_panel.js"
    """

    # Identity
    id: str = Field(..., description="Unique package identifier (slug, no spaces)")
    name: str = Field(..., description="Human-readable package name")
    version: str = Field(..., description="SemVer package version, e.g. '1.0.0'")
    hecos_min_version: str = Field("0.1.0", description="Minimum Hecos version required")
    type: str = Field("plugin", description="Package type: plugin | module | theme | skill_pack")
    author: str = Field("Unknown", description="Author name or organization")
    description: str = Field("", description="Short description of what this package does")

    # Install targets
    target_dir: str = Field(
        "plugins",
        description="Root dir to copy plugin/module code into: 'plugins' or 'modules'"
    )
    plugin_dir: Optional[str] = Field(
        None,
        description="Path inside zip to the plugin/module code folder. Defaults to '<id>/'"
    )

    # Optional WebUI assets
    config_panel: Optional[ConfigPanelDescriptor] = Field(
        None,
        description="Config panel tab descriptor. If present, a tab is injected in the Central Hub."
    )
    widgets: List[WidgetDescriptor] = Field(
        default_factory=list,
        description="List of sidebar/control room widgets bundled with this package"
    )

    # Dependencies
    dependencies: List[str] = Field(
        default_factory=list,
        description="List of other hpkg IDs that must be installed first"
    )
    pip_requirements: List[str] = Field(
        default_factory=list,
        description="List of pip requirements (same syntax as requirements.txt)"
    )

    # Runtime info (extracted into manifest.json for module_scanner)
    tag: Optional[str] = Field(
        None,
        description="Runtime plugin tag (e.g., 'MAIL'). If omitted, defaults to uppercase ID."
    )
    lazy_load: bool = Field(
        True,
        description="Whether this plugin should be lazy loaded at runtime."
    )
    is_class_based: bool = Field(
        True,
        description="Whether the plugin uses the modern class-based structure."
    )
    commands: Dict[str, str] = Field(
        default_factory=dict,
        description="Map of command names to short descriptions for LLM routing."
    )
    tool_schema: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of OpenAI function schemas this plugin provides."
    )
    slash_commands: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of slash commands this plugin registers in chat."
    )

    # Configuration integration
    config_defaults: Dict[str, Any] = Field(
        default_factory=dict,
        description="Default config values to inject into plugins.yaml on install."
    )

    # Integrity
    checksum_sha256: Optional[str] = Field(
        None,
        description="Optional SHA-256 checksum of the .hpkg file itself (without this field). For future signature verification."
    )
    file_hashes: Dict[str, str] = Field(
        default_factory=dict,
        description="SHA-256 hashes of all files in the package. Used for signature verification."
    )

    # Stub fields — reserved for future features
    signature: Optional[str] = Field(
        None,
        description="[FUTURE] Cryptographic signature of the package. Not enforced in this version."
    )
    remote_registry_url: Optional[str] = Field(
        None,
        description="[FUTURE] URL of the remote registry this package was fetched from."
    )

    # Extra metadata passthrough
    extra: Dict[str, Any] = Field(
        default_factory=dict,
        description="Any extra metadata. Preserved but not used by the installer."
    )

    @field_validator("id")
    @classmethod
    def id_must_be_slug(cls, v: str) -> str:
        import re
        if not re.match(r"^[a-z0-9_\-]+$", v):
            raise ValueError(f"Package id '{v}' must be lowercase alphanumeric with underscores/hyphens only.")
        return v

    @field_validator("type")
    @classmethod
    def type_must_be_valid(cls, v: str) -> str:
        valid = {
            "plugin",       # Level 2 — single-responsibility tool
            "module",       # Level 2 — alias kept for backwards compat
            "core_module",  # Level 1 — built-in, not removable
            "extension",    # Level 3 — child of a plugin or core module
            "app",          # Level 4 — autonomous, has its own full UI
            "widget",       # Level 5 — Control Room widget component
            "persona",      # Level 6 — installable AI personality
            "theme",        # Level 7 — CSS/UI theme
            "skill_pack",   # Level 8 — additional HDCS command pack
        }
        if v not in valid:
            raise ValueError(f"Package type '{v}' not valid. Must be one of: {valid}")
        return v

    @field_validator("version", "hecos_min_version")
    @classmethod
    def version_must_be_semver(cls, v: str) -> str:
        import re
        if not re.match(r"^\d+\.\d+(\.\d+)?", v):
            raise ValueError(f"Version '{v}' is not a valid SemVer string.")
        return v
