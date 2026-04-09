"""
MODULE: Extension Loader
DESCRIPTION: Handles discovery and JIT loading of Plugin Extensions.
Extensions are optional sub-modules stored under plugins/<name>/extensions/<ext>/
Each extension follows the same manifest contract as a plugin.
"""

import os
import json
import importlib.util
from zentra.core.logging import logger

# Registry of discovered extensions: {plugin_tag: {ext_id: manifest_data}}
_extension_registry = {}

# Lazy paths for JIT loading: {(plugin_tag, ext_id): abs_path_to_main.py}
_extension_paths = {}


def discover_extensions(plugin_tag: str, plugin_dir: str):
    """
    Scans the extensions/ subfolder of a plugin and registers found extensions.
    Called by plugin_scanner during the capability scan.
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
    return _extension_registry.get(plugin_tag, {})


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
