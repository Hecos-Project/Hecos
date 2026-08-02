from typing import List, Dict, Any
from hecos.core.logging import logger

def get_installed_modules() -> List[Dict[str, Any]]:
    """
    Reads the active module registry to find all installed/loaded modules.
    Uses hecos.core.system.module_loader (already populated at runtime).
    """
    try:
        from hecos.core.system import module_loader
        import inspect

        results = []
        
        # Get all loaded native plugins
        from hecos.core.system.module_state import _loaded_plugins, _loaded_legacy_plugins, _lazy_plugins_paths, _lazy_tool_schemas

        # Native class-based plugins
        for tag, module in _loaded_plugins.items():
            tools_instance = getattr(module, "tools", None)
            results.append({
                "id": tag.lower(),
                "name": getattr(tools_instance, "name", tag),
                "type": getattr(tools_instance, "type", "plugin"),
                "version": getattr(tools_instance, "version", "unknown"),
                "enabled": True,
                "description": getattr(tools_instance, "desc", ""),
                "author": getattr(tools_instance, "author", ""),
                "tags": getattr(tools_instance, "tags", [])
            })

        # Legacy plugins
        for tag, instance in _loaded_legacy_plugins.items():
            info = instance.info() if hasattr(instance, "info") else {}
            results.append({
                "id": tag.lower(),
                "name": info.get("nome", tag),
                "type": "legacy_plugin",
                "version": info.get("version", "unknown"),
                "enabled": True,
                "description": info.get("desc", ""),
                "author": "",
                "tags": []
            })

        # Lazy (dormant) plugins
        for tag in _lazy_plugins_paths:
            if not any(m["id"] == tag.lower() for m in results):
                results.append({
                    "id": tag.lower(),
                    "name": tag,
                    "type": "plugin",
                    "version": "unknown",
                    "enabled": True,
                    "description": "(dormant - not yet loaded)",
                    "author": "",
                    "tags": []
                })

        return results
    except Exception as e:
        logger.error(f"[ModuleAwareness] Failed to read installed modules: {e}")
        return []


def is_module_installed(module_id: str) -> bool:
    """Check if a specific module is installed."""
    modules = get_installed_modules()
    return any(m["id"] == module_id for m in modules)

def get_module_info(module_id: str) -> Dict[str, Any]:
    """Get info for a specific installed module."""
    modules = get_installed_modules()
    for m in modules:
        if m["id"] == module_id:
            return m
    return {}
