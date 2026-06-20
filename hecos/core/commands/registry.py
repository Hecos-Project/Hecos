"""
HDCS — Command Registry
Singleton that collects and exposes all available slash commands from:
  1. Builtins (system_commands, flow_commands)
  2. Plugin auto-discovery (slash_commands attribute on tools class)
"""

import logging
from typing import Optional

_log = logging.getLogger("HecosCommandRegistry")

# ── Command descriptor schema ─────────────────────────────────────────────────
# Each entry in the registry is a dict with these keys:
#
#   id          : str    — unique identifier (no leading slash), e.g. "img"
#   aliases     : list   — all slash forms, e.g. ["/img", "/image", "/foto"]
#   description : str    — short one-line description
#   usage       : str    — syntax hint, e.g. "/img <descrizione>"
#   example     : str    — concrete example
#   icon        : str    — emoji icon
#   category    : str    — "CORE" | "PLUGINS" | "FLOWS"
#   plugin_tag  : str|None — e.g. "IMAGE_GEN" (None for builtins)
#   method      : str|None — method name on the tools object
#   args_schema : dict   — {param: "str"|"str?"|"int"|"int?"}
#   requires_auth: str   — "admin" | "user" | "any"  (default "any")
#   requires_args: bool  — if True, palette shows arg input field


class CommandRegistry:
    """Singleton registry for all HDCS slash commands."""

    def __init__(self):
        self._commands: dict[str, dict] = {}   # keyed by command id
        self._alias_map: dict[str, str] = {}   # alias → command id
        self._loaded = False

    # ── Load ─────────────────────────────────────────────────────────────────

    def load(self, config=None):
        """
        Populate the registry. Safe to call multiple times — clears and reloads.
        Loads builtins first, then plugin-discovered commands.
        """
        self._commands.clear()
        self._alias_map.clear()

        # 1. Builtins
        try:
            from .builtins.system_commands import SYSTEM_COMMANDS
            for cmd in SYSTEM_COMMANDS:
                self._register(cmd)
        except Exception as e:
            _log.error(f"[HDCS Registry] Error loading system builtins: {e}")

        try:
            from .builtins.flow_commands import FLOW_COMMANDS
            for cmd in FLOW_COMMANDS:
                self._register(cmd)
        except Exception as e:
            _log.error(f"[HDCS Registry] Error loading flow builtins: {e}")

        # 2. Plugin auto-discovery
        try:
            from .discovery import discover_plugin_commands
            plugin_cmds = discover_plugin_commands(config=config)
            for cmd in plugin_cmds:
                self._register(cmd)
        except Exception as e:
            _log.error(f"[HDCS Registry] Plugin discovery error: {e}")

        self._loaded = True
        _log.info(f"[HDCS Registry] Loaded {len(self._commands)} commands, {len(self._alias_map)} aliases.")

    def _register(self, cmd: dict):
        """Register a single command descriptor. Silently skips duplicates."""
        cmd_id = cmd.get("id", "").strip()
        if not cmd_id:
            _log.warning(f"[HDCS Registry] Skipping command with no id: {cmd}")
            return

        # Set defaults
        cmd.setdefault("aliases", [f"/{cmd_id}"])
        cmd.setdefault("description", "")
        cmd.setdefault("usage", f"/{cmd_id}")
        cmd.setdefault("example", "")
        cmd.setdefault("icon", "⚡")
        cmd.setdefault("category", "CORE")
        cmd.setdefault("plugin_tag", None)
        cmd.setdefault("method", None)
        cmd.setdefault("args_schema", {})
        cmd.setdefault("requires_auth", "any")   # "any" | "user" | "admin"
        cmd.setdefault("requires_args", False)
        cmd.setdefault("output_target", "chat")  # "chat" | "contextual"

        if cmd_id in self._commands:
            _log.debug(f"[HDCS Registry] Overwriting command id '{cmd_id}'")

        self._commands[cmd_id] = cmd
        for alias in cmd["aliases"]:
            normalized = alias.lower().lstrip("/")
            self._alias_map[normalized] = cmd_id
            # Also map without leading slash just in case
            self._alias_map[alias.lower()] = cmd_id

    # ── Lookup ────────────────────────────────────────────────────────────────

    def _translate_cmd(self, cmd: dict) -> dict:
        """Returns a copy of the command with a translated description if available."""
        from hecos.core.i18n.translator import t
        cmd_copy = cmd.copy()
        # Translate description
        desc_key = f"cmd_desc_{cmd['id'].replace('.', '_')}"
        translated = t(desc_key)
        if translated != desc_key:
            cmd_copy["description"] = translated
        # Translate category if needed
        cat_key = f"cmd_cat_{cmd['category'].lower()}"
        translated_cat = t(cat_key)
        if translated_cat != cat_key:
            cmd_copy["category_translated"] = translated_cat
        else:
            cmd_copy["category_translated"] = cmd["category"]
        return cmd_copy

    def resolve(self, raw_input: str) -> Optional[dict]:
        """
        Given a raw string starting with '/' (e.g. "/img foto di un gatto"),
        return the matching command descriptor or None.
        """
        if not raw_input.startswith("/"):
            return None
        parts = raw_input.strip().split(" ", 1)
        slash_cmd = parts[0].lower()                 # e.g. "/img"
        normalized = slash_cmd.lstrip("/")           # e.g. "img"

        cmd_id = self._alias_map.get(normalized) or self._alias_map.get(slash_cmd)
        if cmd_id:
            cmd = self._commands.get(cmd_id)
            return self._translate_cmd(cmd) if cmd else None
        return None

    def get_all(self) -> list[dict]:
        """Return all registered command descriptors as a list."""
        return [self._translate_cmd(c) for c in self._commands.values()]

    def get_by_category(self, category: str) -> list[dict]:
        return [self._translate_cmd(c) for c in self._commands.values() if c["category"] == category]

    def search(self, query: str) -> list[dict]:
        """Full-text search across id, aliases, description."""
        q = query.lower().lstrip("/")
        results = []
        for cmd in self._commands.values():
            translated_cmd = self._translate_cmd(cmd)
            haystack = (
                translated_cmd["id"] + " " +
                " ".join(translated_cmd["aliases"]) + " " +
                translated_cmd["description"] + " " +
                translated_cmd.get("example", "")
            ).lower()
            if q in haystack:
                results.append(translated_cmd)
        return results

    def is_loaded(self) -> bool:
        return self._loaded


# ── Module-level singleton ────────────────────────────────────────────────────
_registry_instance: Optional[CommandRegistry] = None


def get_registry(config=None, reload: bool = False) -> CommandRegistry:
    """
    Return the global CommandRegistry singleton.
    Lazily initializes on first call.
    Pass reload=True to force a fresh scan (e.g. after new plugins are loaded).
    """
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = CommandRegistry()
    if not _registry_instance.is_loaded() or reload:
        _registry_instance.load(config=config)
    return _registry_instance
