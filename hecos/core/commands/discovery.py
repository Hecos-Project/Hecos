"""
HDCS — Plugin Command Discovery
Scans all loaded plugins for the optional `slash_commands` attribute
on their `tools` class instance and returns a list of command descriptors.

Non-intrusive: plugins without `slash_commands` are silently skipped.
"""

import logging
import os
import json
from typing import Optional

_log = logging.getLogger("HecosCommandDiscovery")


def discover_plugin_commands(config=None) -> list[dict]:
    """
    Generate slash commands for ALL system capabilities.
    1. Reads capabilities from `registry.json` (covers lazy-loaded plugins too).
    2. Synthesizes a generic command `/<tag>.<method>` for every tool method.
    3. Merges explicit friendly aliases (like `/img`) if the module provides them,
       but since modules might be lazy, we rely on auto-generation for full coverage.
    """
    results = []
    
    # 1. Read registry.json for full coverage
    try:
        from hecos.core.system.module_state import REGISTRY_PATH
        if os.path.exists(REGISTRY_PATH):
            with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
                registry_data = json.load(f)
                
            for tag, meta in registry_data.items():
                commands_dict = meta.get("commands", {})
                icon = meta.get("icon", "🔌")
                category = meta.get("category", "PLUGINS")
                
                for method_name, desc in commands_dict.items():
                    cmd_id = f"auto_{tag.lower()}_{method_name}"
                    
                    # Synthesize /tag.method
                    alias = f"/{tag.lower()}.{method_name}"
                    
                    results.append({
                        "id": cmd_id,
                        "aliases": [alias],
                        "description": desc,
                        "plugin_tag": tag,
                        "method": method_name,
                        "requires_args": True, # Most system calls take args, better safe than sorry
                        "icon": icon,
                        "category": category,
                        "output_target": "chat",
                    })

                # Also add explicitly defined friendly aliases
                explicit_cmds = meta.get("slash_commands", [])
                for entry in explicit_cmds:
                    if not isinstance(entry, dict) or not entry.get("id"): continue
                    
                    enriched = dict(entry)
                    enriched.setdefault("plugin_tag", tag)
                    enriched.setdefault("category", category)
                    enriched.setdefault("icon", icon)
                    enriched.setdefault("output_target", "chat")
                    enriched.setdefault("method", entry.get("id"))
                    results.append(enriched)
    except Exception as e:
        _log.warning(f"[HDCS Discovery] Error reading registry.json: {e}")

    # 2. Add explicit friendly aliases from loaded plugins (e eager overrides)
    try:
        from hecos.core.system.module_state import _loaded_plugins
        for tag, module in _loaded_plugins.items():
            tools_obj = getattr(module, "tools", None)
            if not tools_obj: continue
            
            slash_cmds = getattr(tools_obj, "slash_commands", None)
            if not slash_cmds or not isinstance(slash_cmds, list): continue
            
            for entry in slash_cmds:
                if not isinstance(entry, dict) or not entry.get("id"): continue
                
                enriched = dict(entry)
                enriched.setdefault("plugin_tag", tag)
                enriched.setdefault("category", "PLUGINS")
                enriched.setdefault("icon", "🔌")
                enriched.setdefault("output_target", "chat")
                enriched.setdefault("method", entry.get("id"))
                results.append(enriched)
    except Exception as e:
        _log.warning(f"[HDCS Discovery] Error scanning _loaded_plugins: {e}")

    # To deduplicate, if an explicit command maps to the same method, we could merge aliases
    # But executor supports multiple distinct command entries for the same method.
    
    # 3. Specifically extract explicit slash_commands from lazy plugins without full loading
    # (Optional future optimization: Parse AST of lazy plugin main.py)
    # For now, auto-generated commands provide 100% coverage.

    _log.info(f"[HDCS Discovery] Discovered {len(results)} plugin slash commands.")
    return results
