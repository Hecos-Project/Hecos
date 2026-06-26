"""
installer_hooks.py
"""
import importlib.util
import os
from hecos.core.logging import logger
from .package_schema import HpkgManifest

# Types that participate in the system.yaml `plugins` section
# (they have a runtime tag and can be enabled/disabled by the plugin loader)
_PLUGIN_NAMESPACE_TYPES = {"core_module", "plugin", "module", "extension", "app", "skill_pack"}

def run_hook(staging: str, hook_name: str, manifest: HpkgManifest) -> None:
    hooks_path = os.path.join(staging, "install_hooks.py")
    if not os.path.isfile(hooks_path):
        return
    try:
        spec = importlib.util.spec_from_file_location("hpm_hooks", hooks_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        fn = getattr(mod, hook_name, None)
        if callable(fn):
            fn(manifest.model_dump())
            logger.debug(f"[HPM:Installer] Hook '{hook_name}' executed for '{manifest.id}'.")
    except Exception as e:
        logger.warning(f"[HPM:Installer] Hook '{hook_name}' failed for '{manifest.id}': {e}")

def inject_config_defaults(manifest: HpkgManifest) -> None:
    """
    Inject manifest.config_defaults into system.yaml under plugins.<TAG>.
    Skipped for types that don't participate in the plugin namespace
    (e.g. widget-only, persona, theme).
    """
    if not manifest.config_defaults:
        return

    if manifest.type not in _PLUGIN_NAMESPACE_TYPES:
        logger.debug(
            f"[HPM:Installer] Skipping config_defaults injection for "
            f"type '{manifest.type}' ('{manifest.id}') — not a plugin-namespace type."
        )
        return

    try:
        from hecos.app.config import ConfigManager
        cfg_mgr = ConfigManager()
        tag = manifest.tag or manifest.id.upper()
        existing = cfg_mgr.config.get("plugins", {}).get(tag, {})
        needs_save = False
        for k, v in manifest.config_defaults.items():
            if existing.get(k) is None:
                cfg_mgr.set(v, "plugins", tag, k)
                needs_save = True
        if needs_save:
            cfg_mgr.save()
            logger.info(f"[HPM:Installer] Injected default config for '{tag}'.")
    except Exception as e:
        logger.warning(f"[HPM:Installer] Failed to inject config defaults: {e}")

def hot_reload(hecos_root: str) -> None:
    try:
        from hecos.core.system import module_loader
        from hecos.core.system import extension_loader
        from hecos.app.config import ConfigManager
        cfg = ConfigManager().config
        module_loader.update_capability_registry(cfg, debug_log=False)
        webui_dir = os.path.join(hecos_root, "modules", "web_ui")
        extension_loader.discover_webui_extensions(webui_dir)
        logger.info("[HPM:Installer] Capability registry and extensions hot-reloaded.")
    except Exception as e:
        logger.warning(f"[HPM:Installer] Hot-reload failed (non-critical): {e}")
