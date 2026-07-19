"""
routes_packages_helpers.py
─────────────────────────────────────────────────────────────────────────────
Helper functions for HPM Package Manager Routes.
"""
from __future__ import annotations
import os
import json
from hecos.core.logging import logger

# ── Pending Restart Helpers ───────────────────────────────────────────────────
# We use a volatile JSON file instead of a DB column so that:
#   • No SQLite migration is required
#   • The file is automatically cleared at each clean boot
#   • The state is process-safe (written once, read many)

_PENDING_RESTART_TYPES = {"core_module", "plugin", "module", "extension", "app"}


def _get_pending_restart_path() -> str:
    """Absolute path to the pending_restart.json file (hecos/data/)."""
    import sys
    hecos_src = getattr(sys, "_hecos_src_dir", None)
    if not hecos_src:
        import hecos as _hecos_mod
        hecos_src = os.path.dirname(_hecos_mod.__file__)
    return os.path.join(hecos_src, "data", "pending_restart.json")


def _load_pending_restart() -> dict:
    """Return the current pending_restart dict, e.g. {pkg_id: True}."""
    path = _get_pending_restart_path()
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def add_to_pending_restart(pkg_id: str) -> None:
    """Mark pkg_id as requiring a restart before it is fully functional."""
    path = _get_pending_restart_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = _load_pending_restart()
    data[pkg_id] = True
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        logger.info(f"[HPM] Package '{pkg_id}' marked as pending restart.")
    except Exception as e:
        logger.warning(f"[HPM] Could not write pending_restart.json: {e}")


def clear_pending_restart() -> None:
    """Delete the pending_restart.json file — called on clean server boot."""
    path = _get_pending_restart_path()
    try:
        if os.path.exists(path):
            os.remove(path)
            logger.info("[HPM] pending_restart.json cleared on boot.")
    except Exception as e:
        logger.warning(f"[HPM] Could not clear pending_restart.json: {e}")


def get_pending_restart_ids() -> set:
    """Return the set of package IDs that require a restart."""
    return set(_load_pending_restart().keys())


def remove_from_pending_restart(pkg_id: str) -> None:
    """Remove a single pkg_id from the pending restart list."""
    path = _get_pending_restart_path()
    data = _load_pending_restart()
    if pkg_id in data:
        del data[pkg_id]
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception as e:
            logger.warning(f"[HPM] Could not update pending_restart.json: {e}")

# ─────────────────────────────────────────────────────────────────────────────

def _get_hpm_components(hecos_root: str):
    """
    Lazily initialize HPM components. Keeps them as module-level singletons
    so the registry connection is reused across requests.
    """
    import sys
    if not hasattr(sys, "_hecos_hpm_registry"):
        from hecos.core.package_manager.registry import PackageRegistry
        from hecos.core.package_manager.installer import PackageInstaller
        from hecos.core.package_manager.uninstaller import PackageUninstaller
        from hecos.core.system.version import VERSION

        data_dir = os.path.join(hecos_root, "data")
        os.makedirs(data_dir, exist_ok=True)

        cfg_mgr = getattr(sys, "_hecos_cfg_mgr", None)

        registry = PackageRegistry(data_dir=data_dir)
        installer = PackageInstaller(
            hecos_root=hecos_root,
            registry=registry,
            hecos_version=VERSION,
            event_callback=_hpm_event_broadcast,
            cfg_mgr=cfg_mgr
        )
        uninstaller = PackageUninstaller(
            hecos_root=hecos_root,
            registry=registry,
            event_callback=_hpm_event_broadcast,
        )

        sys._hecos_hpm_registry = registry
        sys._hecos_hpm_installer = installer
        sys._hecos_hpm_uninstaller = uninstaller

    return (
        sys._hecos_hpm_registry,
        sys._hecos_hpm_installer,
        sys._hecos_hpm_uninstaller,
    )


def _hpm_event_broadcast(event_name: str, payload: dict) -> None:
    """Broadcast HPM events to connected WebUI clients via SSE."""
    try:
        import sys
        sm = getattr(sys, "hecos_state_manager", None)
        if sm and hasattr(sm, "add_event"):
            sm.add_event(event_name, payload)
            logger.debug(f"[HPM:Routes] Event broadcast: {event_name} → {payload.get('id')}")
    except Exception as e:
        logger.debug(f"[HPM:Routes] Could not broadcast event: {e}")


def _refresh_jinja_loader(app) -> None:
    """
    Hot-reload the Jinja2 template loader to:
    - ADD template directories from newly installed extensions.
    - REMOVE template directories from uninstalled extensions (path no longer on disk).
    Safe to call multiple times — deduplicates paths automatically.
    """
    try:
        from jinja2 import FileSystemLoader, ChoiceLoader
        import sys
        hecos_src = getattr(sys, "_hecos_src_dir", None)
        if not hecos_src:
            return
        ext_root = os.path.join(hecos_src, "modules", "web_ui", "extensions")

        # Collect all existing loader paths to compare
        current = app.jinja_loader
        current_loaders = []
        if isinstance(current, ChoiceLoader):
            current_loaders = list(current.loaders)
        else:
            current_loaders = [current]

        # Scan which extension template dirs actually exist on disk right now
        existing_tpl_dirs = set()
        if os.path.isdir(ext_root):
            for ext_name in os.listdir(ext_root):
                tpl_dir = os.path.join(ext_root, ext_name, "templates")
                if os.path.isdir(tpl_dir):
                    existing_tpl_dirs.add(os.path.normcase(os.path.abspath(tpl_dir)))

        # Build the new loader list:
        # - Keep non-extension loaders (core templates, etc.) always
        # - Keep extension loaders only if the path still exists on disk
        # - Add any new paths not already present
        new_loaders = []
        seen_paths = set()

        for ldr in current_loaders:
            if isinstance(ldr, FileSystemLoader):
                # Check if this is an extension template dir
                kept_paths = []
                for p in ldr.searchpath:
                    norm = os.path.normcase(os.path.abspath(p))
                    # If it's under ext_root, only keep it if it still exists
                    is_ext_path = norm.startswith(os.path.normcase(os.path.abspath(ext_root))) if os.path.isdir(ext_root) else False
                    if is_ext_path:
                        if norm in existing_tpl_dirs and norm not in seen_paths:
                            kept_paths.append(p)
                            seen_paths.add(norm)
                    else:
                        # Non-extension path — always keep
                        if norm not in seen_paths:
                            kept_paths.append(p)
                            seen_paths.add(norm)
                if kept_paths:
                    if len(kept_paths) == len(ldr.searchpath):
                        new_loaders.append(ldr)  # Unchanged loader, keep reference
                    else:
                        new_loaders.append(FileSystemLoader(kept_paths))
            else:
                new_loaders.append(ldr)

        # Add NEW extension dirs not yet in the loader
        for tpl_dir in sorted(existing_tpl_dirs):
            if tpl_dir not in seen_paths:
                new_loaders.append(FileSystemLoader(tpl_dir))
                logger.info(f"[HPM:Routes] Jinja loader hot-patched: +{tpl_dir}")

        if len(new_loaders) == 1:
            app.jinja_loader = new_loaders[0]
        else:
            app.jinja_loader = ChoiceLoader(new_loaders)

    except Exception as _e:
        logger.warning(f"[HPM:Routes] _refresh_jinja_loader failed: {_e}")
