"""
installer_steps.py
"""
import os
import shutil
from typing import List
from hecos.core.logging import logger
from .package_schema import HpkgManifest

# ── Default target directory per module type ────────────────────────────────
# Used when the manifest does not override `target_dir` explicitly.
# Types with no backend code (widget) don't need a code install directory.
TYPE_DEFAULT_DIR = {
    "core_module": "plugins",
    "plugin":      "plugins",
    "module":      "plugins",
    "extension":   "plugins",
    "app":         "apps",
    "widget":      None,          # widget-only: no backend, skip code install
    "persona":     "personas",
    "theme":       "themes",
    "skill_pack":  "skill_packs",
}

def copy_tree(src: str, dst: str) -> List[str]:
    copied: List[str] = []
    for root, _, files in os.walk(src):
        rel = os.path.relpath(root, src)
        dest_dir = os.path.join(dst, rel) if rel != "." else dst
        os.makedirs(dest_dir, exist_ok=True)
        for fname in files:
            src_file = os.path.join(root, fname)
            dst_file = os.path.join(dest_dir, fname)
            shutil.copy2(src_file, dst_file)
            copied.append(dst_file)
    return copied

def rollback(installed_files: List[str], pkg_id: str) -> None:
    logger.warning(f"[HPM:Installer] Rolling back installation of '{pkg_id}' ({len(installed_files)} files)...")
    for fp in installed_files:
        try:
            if os.path.isfile(fp):
                os.remove(fp)
        except Exception as e:
            logger.error(f"[HPM:Installer] Rollback: could not remove '{fp}': {e}")
    logger.info(f"[HPM:Installer] Rollback complete for '{pkg_id}'.")


def _resolve_target_dir(manifest: HpkgManifest) -> str | None:
    """
    Return the resolved target directory for this package type.
    Returns None for types that have no backend code to install (e.g. widget).
    If `manifest.target_dir` is explicitly set to something other than 'plugins'
    (the schema default), we honour that override.
    """
    pkg_type = manifest.type
    default_for_type = TYPE_DEFAULT_DIR.get(pkg_type)

    # If the developer explicitly overrode target_dir away from the default 'plugins',
    # respect their choice — but only if this type normally HAS a target directory.
    if default_for_type is not None and manifest.target_dir != "plugins":
        return manifest.target_dir

    return default_for_type


def install_plugin_code(staging: str, manifest: HpkgManifest, hecos_root: str) -> List[str]:
    # Determine the target directory based on module type
    target_dir_name = _resolve_target_dir(manifest)

    if target_dir_name is None:
        logger.info(
            f"[HPM:Installer] Type '{manifest.type}' has no backend code — "
            f"skipping code install for '{manifest.id}'."
        )
        return []

    plugin_dir_in_zip = manifest.plugin_dir or f"{manifest.id}/"
    plugin_src = os.path.join(staging, plugin_dir_in_zip.rstrip("/"))

    if not os.path.isdir(plugin_src):
        for candidate in ["plugin", "module", "app", manifest.id]:
            candidate_path = os.path.join(staging, candidate)
            if os.path.isdir(candidate_path):
                plugin_src = candidate_path
                break
        else:
            logger.warning(f"[HPM:Installer] No plugin code directory found in package '{manifest.id}'. Skipping code install.")
            return []

    target_base = os.path.join(hecos_root, target_dir_name)
    os.makedirs(target_base, exist_ok=True)
    target_dir = os.path.join(target_base, manifest.id)

    copied_files = copy_tree(plugin_src, target_dir)

    runtime_manifest_path = os.path.join(target_dir, "manifest.json")
    import json
    runtime_manifest_data = {}
    if os.path.exists(runtime_manifest_path):
        try:
            with open(runtime_manifest_path, "r", encoding="utf-8") as f:
                runtime_manifest_data = json.load(f)
        except Exception as e:
            logger.warning(f"Could not read existing manifest.json: {e}")

    runtime_manifest_data.update({
        "tag": manifest.tag or manifest.id.upper(),
        "name": manifest.name,
        "version": manifest.version,
        "description": manifest.description,
        "lazy_load": manifest.lazy_load,
        "is_class_based": manifest.is_class_based,
        "commands": manifest.commands,
        "tool_schema": manifest.tool_schema,
        "slash_commands": manifest.slash_commands,
    })
    if manifest.config_panel:
        runtime_manifest_data["icon"] = manifest.config_panel.tab_icon
        
    with open(runtime_manifest_path, "w", encoding="utf-8") as f:
        json.dump(runtime_manifest_data, f, indent=4)
    
    if runtime_manifest_path not in copied_files:
        copied_files.append(runtime_manifest_path)
    return copied_files


def install_webui_assets(staging: str, manifest: HpkgManifest, hecos_root: str) -> List[str]:
    webui_src = os.path.join(staging, "web_ui")
    if not os.path.isdir(webui_src):
        return []
    webui_base = os.path.join(hecos_root, "modules", "web_ui")
    installed: List[str] = []

    templates_src = os.path.join(webui_src, "templates")
    if os.path.isdir(templates_src):
        templates_dst = os.path.join(webui_base, "templates", "modules")
        installed.extend(copy_tree(templates_src, templates_dst))

    static_src = os.path.join(webui_src, "static")
    if os.path.isdir(static_src):
        static_dst = os.path.join(webui_base, "static")
        installed.extend(copy_tree(static_src, static_dst))

    return installed


def install_widgets(staging: str, manifest: HpkgManifest, hecos_root: str) -> List[str]:
    if not manifest.widgets:
        return []
    installed: List[str] = []
    ext_base = os.path.join(hecos_root, "modules", "web_ui", "extensions")
    os.makedirs(ext_base, exist_ok=True)

    for w in manifest.widgets:
        src = os.path.join(staging, w.extension_path.rstrip("/"))
        if not os.path.isdir(src):
            logger.warning(f"[HPM:Installer] Widget source '{w.extension_path}' not found in package.")
            continue
        widget_name = os.path.basename(src)
        dst = os.path.join(ext_base, widget_name)
        installed.extend(copy_tree(src, dst))

    return installed


def install_i18n(staging: str, manifest: HpkgManifest, hecos_root: str) -> List[str]:
    i18n_src = os.path.join(staging, "i18n")
    if not os.path.isdir(i18n_src):
        return []
    i18n_dst = os.path.join(hecos_root, "core", "i18n", "locales")
    os.makedirs(i18n_dst, exist_ok=True)
    return copy_tree(i18n_src, i18n_dst)
