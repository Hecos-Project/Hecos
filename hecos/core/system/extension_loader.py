"""
MODULE: Extension Loader
DESCRIPTION: Handles discovery and JIT loading of Plugin Extensions.
Extensions are optional sub-modules stored under plugins/<name>/extensions/<ext>/
WEB_UI Shared Extensions live under modules/web_ui/extensions/<ext>/
Each extension follows the same manifest contract as a plugin.
"""

import os
import json
import importlib.util
from hecos.core.logging import logger

# Registry of discovered extensions: {plugin_tag: {ext_id: manifest_data}}
_extension_registry = {}

# Lazy paths for JIT loading: {(plugin_tag, ext_id): abs_path_to_main.py}
_extension_paths = {}


def discover_extensions(plugin_tag: str, plugin_dir: str):
    """
    Scans the extensions/ subfolder of a plugin and registers found extensions.
    Called by module_scanner during the capability scan.
    """
    ext_root = os.path.join(plugin_dir, "extensions")
    if not os.path.isdir(ext_root):
        return

    for ext_name in os.listdir(ext_root):
        ext_dir = os.path.join(ext_root, ext_name)
        if not os.path.isdir(ext_dir):
            continue

        manifest_path = os.path.join(ext_dir, "manifest.json")
        main_path = os.path.join(ext_dir, "main.py")

        if not os.path.exists(manifest_path) or not os.path.exists(main_path):
            logger.debug("EXT_LOADER", f"Extension {ext_name} missing manifest or main.py, skipped.")
            continue

        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)

            ext_id = manifest.get("extension_id", ext_name)

            if plugin_tag not in _extension_registry:
                _extension_registry[plugin_tag] = {}

            _extension_registry[plugin_tag][ext_id] = manifest
            _extension_paths[(plugin_tag, ext_id)] = os.path.abspath(main_path)

            logger.debug("EXT_LOADER", f"Extension registered: [{plugin_tag}] → [{ext_id}]")
        except Exception as e:
            logger.error(f"EXT_LOADER: Failed to parse extension manifest {manifest_path}: {e}")


def get_extension_config(plugin_tag: str, ext_id: str) -> dict:
    """
    Returns the config schema defaults for an extension.
    Can be overridden by system.yaml in the future.
    """
    manifest = _extension_registry.get(plugin_tag, {}).get(ext_id, {})
    schema = manifest.get("config_schema", {})
    return {k: v.get("default") for k, v in schema.items()}


def get_registered_extensions(plugin_tag: str) -> dict:
    """Returns all registered extension manifests for a given plugin."""
    return _extension_registry.get(plugin_tag, {})\


def _is_plugin_active(required_plugin: str, config: dict) -> bool:
    """
    Checks whether the plugin identified by `required_plugin` tag is enabled
    in the given config dict. Returns True if no config is given (permissive default).
    """
    if not config or not required_plugin:
        return True
    return config.get("plugins", {}).get(required_plugin, {}).get("enabled", True)


def _get_widget_prefs(ext_id: str, config: dict) -> dict:
    """
    Returns the per-widget user preferences from config["widgets"]["per_widget"][ext_id].
    Defaults: visible=True.
    """
    if not config:
        return {"visible": True}
    prefs = config.get("widgets", {}).get("per_widget", {}).get(ext_id, {})
    return {
        "visible": prefs.get("visible", True),
    }


def _sidebar_order(config: dict) -> list:
    """Returns the user-defined sidebar order list from config, or empty list."""
    if not config:
        return []
    return config.get("widgets", {}).get("sidebar_order", [])


def get_sidebar_widgets(config: dict = None) -> list:
    """
    Returns a list of manifests for widgets that should be in the sidebar.
    Considers parent plugin status, user visibility preference, and custom order.
    """
    # 1. Get all candidates
    all_widgets = get_all_widgets(config)
    
    # 2. Filter by active and visible
    visible_widgets = {w["extension_id"]: w for w in all_widgets if w.get("plugin_active") and w.get("visible")}
    
    # 3. Apply order
    if not config:
        return list(visible_widgets.values())
        
    order = config.get("widgets", {}).get("sidebar_order", [])
    result = []
    
    # First, add widgets that are in the ordered list (if they are visible)
    for ext_id in order:
        if ext_id in visible_widgets:
            result.append(visible_widgets.pop(ext_id))
            
    # Then, append any remaining visible widgets that weren't in the explicit order list
    # (this ensures new widgets or unordered ones don't disappear)
    for ext_id, manifest in visible_widgets.items():
        result.append(manifest)
        
    return result


def get_all_widgets(config: dict = None) -> list:
    """
    Returns ALL WEB_UI sidebar widgets as enriched dicts for the Widget Manager panel.
    Includes disabled/hidden widgets with their status.

    Each item contains:
      - All manifest fields
      - plugin_active (bool): whether the required_plugin is currently enabled
      - visible (bool): user visibility preference
      - order_index (int): current position in sidebar_order (None if not set)
    """
    all_webui = _extension_registry.get("WEB_UI", {})
    order = _sidebar_order(config)

    result = []
    for ext_id, manifest in all_webui.items():
        if not manifest.get("sidebar_widget", False):
            continue

        req_plugin = manifest.get("required_plugin")
        plugin_active = _is_plugin_active(req_plugin, config)
        prefs = _get_widget_prefs(ext_id, config)

        try:
            order_index = order.index(ext_id)
        except ValueError:
            order_index = None

        enriched = dict(manifest)
        enriched["extension_id"] = ext_id # Ensure it's there even if manifest.json missed it
        enriched["plugin_active"] = plugin_active
        enriched["visible"] = prefs.get("visible", True)
        enriched["order_index"] = order_index
        result.append(enriched)

    # Sort: widgets with an explicit order index first, then by discovery order
    result.sort(key=lambda m: (m["order_index"] is None, m["order_index"] or 0))
    return result


def discover_webui_extensions(webui_module_dir: str):
    """
    Scans modules/web_ui/extensions/ and registers found extensions under
    the synthetic 'WEB_UI' parent tag.  Called once during server boot.
    """
    discover_extensions("WEB_UI", webui_module_dir)


def load_eager_extensions(app, plugin_tag: str):
    """
    Immediately loads all extensions for *plugin_tag* that have 'eager_load': true.
    Should be called after discover_extensions() so the registry is populated.
    """
    for ext_id, manifest in _extension_registry.get(plugin_tag, {}).items():
        if manifest.get("eager_load", False):
            load_extension_routes(app, plugin_tag, ext_id)


def load_extension_routes(app, plugin_tag: str, ext_id: str):
    """
    JIT loads an extension's main.py and calls init_routes(app) if defined.
    Safe to call multiple times — subsequent calls are no-ops if already loaded.
    """
    key = (plugin_tag, ext_id)
    main_path = _extension_paths.get(key)


    if not main_path or not os.path.exists(main_path):
        logger.error(f"EXT_LOADER: Extension [{plugin_tag}:{ext_id}] not found or not registered.")
        return False

    try:
        plugin_dir = os.path.basename(os.path.dirname(os.path.dirname(os.path.dirname(main_path))))
        module_name = f"plugins.{plugin_dir}.extensions.{ext_id}.main"


        spec = importlib.util.spec_from_file_location(module_name, main_path)
        if not spec:
            return False

        module = importlib.util.module_from_spec(spec)
        import sys
        sys.modules[module_name] = module

        spec.loader.exec_module(module)


        if hasattr(module, "init_routes"):
            module.init_routes(app)
            logger.debug("EXT_LOADER", f"Extension [{plugin_tag}:{ext_id}] routes registered.")

        return True
    except Exception as e:
        import traceback
        logger.error(f"EXT_LOADER: Failed to load extension [{plugin_tag}:{ext_id}]: {e}")
        return False
