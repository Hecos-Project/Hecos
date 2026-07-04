"""
capability_inspector.py — Hecos Core
=====================================
Builds a ModuleCapabilityCard for any installed Hecos plugin/widget.

Two modes:
  - Static  (always on): reads [capabilities] from hpkg_manifest.toml
  - Introspection (opt-in): uses Python `inspect` to augment static data
    at runtime — zero LLM, zero network, pure Python analysis.

Toggle introspection via config:
    hpm.auto_introspect = true   (system.yaml or packages.db setting)
"""
from __future__ import annotations

import inspect
import os
from dataclasses import dataclass, field
from typing import Any


# ── Dataclass ────────────────────────────────────────────────────────────────

@dataclass
class ModuleCapabilityCard:
    """Unified capability profile for a Hecos package."""
    # Identity
    id:               str
    name:             str
    version:          str
    type:             str          # plugin | widget | module | hybrid
    author:           str
    description:      str

    # Static capabilities (from [capabilities] in hpkg_manifest.toml)
    llm_tools:        list[str] = field(default_factory=list)
    slash_commands:   list[str] = field(default_factory=list)
    has_widget:       bool = False
    has_config_panel: bool = False
    has_api_routes:   bool = False
    has_system_calls: bool = False
    syscall_notes:    str  = ""
    notes:            str  = ""

    # Auto-detected (populated only if introspection is enabled)
    auto_tools:       list[dict] = field(default_factory=list)   # [{name, doc}]
    auto_commands:    list[str]  = field(default_factory=list)
    auto_routes:      list[str]  = field(default_factory=list)
    introspected:     bool = False

    def format_card(self, compact: bool = False) -> str:
        """Render the card as a formatted text string."""
        lines = []
        icon = "🧩" if self.type == "plugin" else "📦" if self.type == "widget" else "⚙️"
        lines.append(f"╔{'═' * 46}╗")
        lines.append(f"║  {icon}  {self.name}  v{self.version:<36}║")
        lines.append(f"║  {self.type.capitalize():<12} · by {self.author:<28}║")
        lines.append(f"╠{'═' * 46}╣")

        # LLM tools
        tools = self.llm_tools or (
            [t["name"] for t in self.auto_tools] if self.introspected else []
        )
        if tools:
            lines.append(f"║  LLM Tools ({len(tools)}):{' ' * (33 - len(str(len(tools))))}║")
            for t in tools[:8]:
                lines.append(f"║    · {t:<42}║")
            if len(tools) > 8:
                lines.append(f"║    … +{len(tools) - 8} more{' ' * 37}║")
        else:
            lines.append(f"║  LLM Tools: none{' ' * 31}║")

        # Commands
        cmds = self.slash_commands or self.auto_commands
        if cmds:
            lines.append(f"║  Direct Commands ({len(cmds)}): {', '.join(cmds[:4]):<26}║")
        else:
            lines.append(f"║  Direct Commands (/): none{' ' * 21}║")

        lines.append(f"╠{'═' * 46}╣")
        lines.append(f"║  Widget: {'✓' if self.has_widget else '✗'}  "
                     f"Config Panel: {'✓' if self.has_config_panel else '✗'}  "
                     f"API Routes: {'✓' if self.has_api_routes else '✗'}{'  ' * 3}║")
        syscall_marker = "✓" if self.has_system_calls else "✗"
        lines.append(f"║  System Calls: {syscall_marker:<32}║")

        if self.syscall_notes:
            note = self.syscall_notes[:44]
            lines.append(f"║  └─ {note:<42}║")

        if self.notes and not compact:
            # Word-wrap notes at 44 chars
            words = self.notes.split()
            row = ""
            for w in words:
                if len(row) + len(w) + 1 > 44:
                    lines.append(f"║  {row:<44}║")
                    row = w
                else:
                    row = f"{row} {w}".strip()
            if row:
                lines.append(f"║  {row:<44}║")

        if self.introspected:
            lines.append(f"╠{'═' * 46}╣")
            lines.append(f"║  🔍 Auto-detected capabilities{' ' * 17}║")
            if self.auto_routes:
                lines.append(f"║  Routes: {', '.join(self.auto_routes[:3]):<36}║")

        lines.append(f"╚{'═' * 46}╝")
        return "\n".join(lines)


# ── Builder ───────────────────────────────────────────────────────────────────

def build_card(plugin_id: str, introspect: bool = False) -> ModuleCapabilityCard | None:
    """
    Build a capability card for the given plugin_id.

    Args:
        plugin_id:  The package ID (e.g. 'webcam', 'calendar', 'lists').
        introspect: If True, augment static data with Python inspect analysis.

    Returns:
        ModuleCapabilityCard or None if the package is not installed/found.
    """
    manifest = _load_installed_manifest(plugin_id)
    if not manifest:
        return None

    cap = manifest.get("capabilities", {})

    card = ModuleCapabilityCard(
        id           = manifest.get("id", plugin_id),
        name         = manifest.get("name", plugin_id),
        version      = manifest.get("version", "?"),
        type         = manifest.get("type", "plugin"),
        author       = manifest.get("author", "unknown"),
        description  = manifest.get("description", ""),
        llm_tools    = cap.get("llm_tools", []),
        slash_commands = cap.get("slash_commands", []),
        has_widget       = cap.get("has_widget", False),
        has_config_panel = cap.get("has_config_panel", False),
        has_api_routes   = cap.get("has_api_routes", False),
        has_system_calls = cap.get("has_system_calls", False),
        syscall_notes    = cap.get("syscall_notes", ""),
        notes            = cap.get("notes", ""),
    )

    if introspect:
        _run_introspection(card, plugin_id, manifest)

    return card


def build_all_cards(introspect: bool = False) -> list[ModuleCapabilityCard]:
    """Return capability cards for all installed packages."""
    try:
        from hecos.core.package_manager.registry import PackageRegistry
        registry = PackageRegistry(_get_hecos_root() + "/data")
        ids = [p["id"] for p in registry.list_all()]
    except Exception:
        ids = _discover_plugin_ids()

    cards = []
    for pid in ids:
        card = build_card(pid, introspect=introspect)
        if card:
            cards.append(card)
    return sorted(cards, key=lambda c: c.name.lower())


# ── Internal helpers ──────────────────────────────────────────────────────────

def _load_installed_manifest(plugin_id: str) -> dict[str, Any] | None:
    """
    Try to load the hpkg_manifest.toml for an installed package.
    Checks packages.db registry first, then fallback to filesystem.
    """
    hecos_root = _get_hecos_root()
    
    # 1. Primary: check packages DB for manifest data
    try:
        from hecos.core.package_manager.registry import PackageRegistry
        registry = PackageRegistry(hecos_root + "/data")
        pkg = registry.get(plugin_id)
        if pkg and pkg.get("manifest_snapshot"):
            snap = pkg["manifest_snapshot"]
            if isinstance(snap, dict):
                return snap
            import json
            return json.loads(snap)
    except Exception as e:
        pass

    # 2. Fallback to filesystem
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore
        except ImportError:
            return None

    candidates = [
        os.path.join(hecos_root, "hpm", plugin_id, "hpkg_manifest.toml"),
        os.path.join(hecos_root, "plugins", plugin_id, "hpkg_manifest.toml"),
        os.path.join(hecos_root, "modules", "web_ui", "extensions", plugin_id, "hpkg_manifest.toml"),
    ]

    for path in candidates:
        if os.path.isfile(path):
            try:
                with open(path, "rb") as f:
                    return tomllib.load(f)
            except Exception:
                pass

    return None


def _run_introspection(card: ModuleCapabilityCard, plugin_id: str, manifest: dict) -> None:
    """
    Use Python `inspect` to augment static card data.
    Discovers: public methods with docstrings, registered commands, Flask routes.
    No LLM, no network — pure Python analysis.
    """
    tag = manifest.get("tag", plugin_id.upper())

    # 1. Inspect plugin class methods
    try:
        try:
            mod = importlib.import_module(f"hecos.hpm.{plugin_id}.main")
        except ImportError:
            mod = importlib.import_module(f"hecos.plugins.{plugin_id}.main")
        
        classes = inspect.getmembers(mod, inspect.isclass)
        for _, cls in classes:
            if cls.__module__ == mod.__name__:
                methods = inspect.getmembers(cls, predicate=inspect.isfunction)
                for name, func in methods:
                    if name.startswith("_"):
                        continue
                    doc = inspect.getdoc(func) or ""
                    card.auto_tools.append({"name": name, "doc": doc[:120]})
    except Exception:
        pass

    # 2. Scan command registry for this plugin's commands
    try:
        from hecos.core.commands.registry import CommandRegistry
        registry = CommandRegistry.instance()
        if registry:
            all_cmds = registry.get_all_commands()
            card.auto_commands = [
                cmd for cmd in all_cmds
                if cmd.get("plugin_tag", "").upper() == tag.upper()
            ]
    except Exception:
        pass

    # 3. Scan Flask app routes for this plugin's endpoints
    try:
        from hecos.modules.web_ui.server_flask import get_app
        app = get_app()
        if app:
            prefix_plugin = f"/hecos/api/plugins/{plugin_id}"
            prefix_hpm    = f"/hecos/api/hpm/{plugin_id}"
            card.auto_routes = [
                rule.rule for rule in app.url_map.iter_rules()
                if rule.rule.startswith(prefix_plugin) or rule.rule.startswith(prefix_hpm)
            ]
    except Exception:
        pass

    card.introspected = True


def _get_hecos_root() -> str:
    """Walk up from this file to reach the hecos package root."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _discover_plugin_ids() -> list[str]:
    """Fallback: scan hpm/ and plugins/ directories for installed plugin IDs."""
    root = _get_hecos_root()
    found = []
    
    for d_name in ["hpm", "plugins"]:
        scan_dir = os.path.join(root, d_name)
        if os.path.isdir(scan_dir):
            for d in os.listdir(scan_dir):
                if os.path.isdir(os.path.join(scan_dir, d)) and not d.startswith("_"):
                    if d not in found:
                        found.append(d)
    
    return found
