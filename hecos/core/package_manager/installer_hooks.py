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
    Deprecated in 0.40.0.
    Config injection into system.yaml is no longer supported.
    Packages must use HPMBaseConfigManager (Pydantic+TOML) instead.
    """
    if manifest.config_defaults:
        logger.warning(
            f"[HPM:Installer] Package '{manifest.id}' uses deprecated 'config_defaults'. "
            f"This is no longer supported in Hecos 0.40+. Please migrate to HPMBaseConfigManager."
        )

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
