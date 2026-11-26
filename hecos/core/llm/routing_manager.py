import json
import os
try:
    import tomllib
except ImportError:
    tomllib = None
from hecos.core.logging import logger
from hecos.core.system.module_loader import get_active_tags
from hecos.config import load_yaml

# Replicate the constants needed for routing
_HECOS_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
REGISTRY_PATH = os.path.join(_HECOS_DIR, "core", "registry.json")


def _extract_snapshot_dict(raw_snap):
    """Safely normalize PackageRegistry manifest_snapshot (dict or JSON string)."""
    if isinstance(raw_snap, dict):
        return raw_snap
    if isinstance(raw_snap, str) and raw_snap.strip():
        try:
            parsed = json.loads(raw_snap)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def _read_hpkg_manifest_routing(install_path):
    """Read [routing].instructions from hpkg_manifest.toml inside a package root."""
    if not install_path or tomllib is None:
        return ""
    toml_path = os.path.join(install_path, "hpkg_manifest.toml")
    if not os.path.isfile(toml_path):
        return ""
    try:
        with open(toml_path, "rb") as tf:
            data = tomllib.load(tf)
        routing = data.get("routing")
        if isinstance(routing, dict):
            return str(routing.get("instructions") or "").strip()
    except Exception:
        return ""
    return ""


class RoutingManager:
    """
    Manages the hybrid routing system:
    1. HPM routing_override.yaml (User-editable override — can override or disable)
    2. HPM Manifest ([routing].instructions in manifest_snapshot or hpkg_manifest.toml)
    3. Legacy Core Registry (Fallback)
    """
    @staticmethod
    def get_dynamic_instructions(config):
        try:
            # 1. Load active plugin tags (deduplicated), filtered by per-session/preset payload_control
            raw_tags = get_active_tags()
            if not raw_tags:
                try:
                    from hecos.core.system.module_loader import update_capability_registry
                    update_capability_registry(config, debug_log=False)
                    raw_tags = get_active_tags()
                except Exception as _reg_err:
                    logger.debug(f"RoutingManager: capability update skipped: {_reg_err}")

            active_tags = []
            seen_upper = set()
            for t in (raw_tags or []):
                tu = str(t or "").strip().upper()
                if tu and tu not in seen_upper:
                    seen_upper.add(tu)
                    active_tags.append(tu)

            p_ctrl = (config.get("payload_control") or {}) if isinstance(config, dict) else {}
            if config and (config.get("disable_tools", False) or not p_ctrl.get("send_tools", True)):
                return ""
            sel_mode = str(p_ctrl.get("tool_selection_mode") or "all").strip().lower()
            custom_allowed_tags = None
            if sel_mode == "custom":
                custom_allowed_tags = {
                    (str(item).strip().split("__", 1)[0].upper() if "__" in str(item) else str(item).strip().upper())
                    for item in (p_ctrl.get("selected_tools") or [])
                    if str(item).strip()
                }
                if not custom_allowed_tags:
                    return ""

            # 2. Load instructions from registry
            registry_data = {}
            if os.path.exists(REGISTRY_PATH):
                with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
                    registry_data = json.load(f)

            # 3. Build tag -> installed HPM package index (by id, tag, plugin_tag, install dir name)
            hpm_by_key = {}
            try:
                from hecos.core.package_manager.registry import PackageRegistry
                hpm_registry = PackageRegistry(os.path.join(_HECOS_DIR, "data"))
                for pkg in (hpm_registry.list_all() or []):
                    if pkg.get("status") != "installed":
                        continue
                    snap = _extract_snapshot_dict(pkg.get("manifest_snapshot"))
                    extra = snap.get("extra") if isinstance(snap.get("extra"), dict) else {}
                    keys = set()
                    for cand in (
                        pkg.get("id"),
                        pkg.get("tag"),
                        snap.get("tag"),
                        extra.get("plugin_tag"),
                        os.path.basename(pkg.get("install_path") or ""),
                    ):
                        c = str(cand or "").strip().lower()
                        if c:
                            keys.add(c)
                    for k in keys:
                        hpm_by_key.setdefault(k, (pkg, snap))
            except Exception as _hpm_err:
                logger.debug(f"RoutingManager: HPM registry lookup skipped: {_hpm_err}")

            # 4. Merge routing instructions cleanly
            merged_instructions = []

            for tag_upper in active_tags:
                tag_lower = tag_upper.lower()
                if custom_allowed_tags is not None and tag_upper not in custom_allowed_tags:
                    continue

                instruction = None
                explicitly_disabled = False

                # Check HPM package (override file > manifest_snapshot > hpkg_manifest.toml)
                pkg_entry = hpm_by_key.get(tag_lower)
                if pkg_entry:
                    pkg, snap = pkg_entry
                    install_path = pkg.get("install_path") or ""

                    if install_path:
                        dyn_file = os.path.join(install_path, "routing_override.yaml")
                        if os.path.exists(dyn_file):
                            try:
                                import yaml
                                with open(dyn_file, "r", encoding="utf-8") as df:
                                    y_data = yaml.safe_load(df)
                                if isinstance(y_data, dict):
                                    if y_data.get("enabled", True) is False:
                                        explicitly_disabled = True
                                    else:
                                        override_txt = str(y_data.get("instruction") or "").strip()
                                        if override_txt:
                                            instruction = override_txt
                            except Exception:
                                pass

                    if not instruction and not explicitly_disabled:
                        routing_block = snap.get("routing")
                        if not isinstance(routing_block, dict) and isinstance(snap.get("extra"), dict):
                            routing_block = snap["extra"].get("routing")
                        if isinstance(routing_block, dict):
                            instruction = str(routing_block.get("instructions") or "").strip() or None

                    if not instruction and not explicitly_disabled and install_path:
                        instruction = _read_hpkg_manifest_routing(install_path) or None

                # Fallback to legacy registry (unless explicitly disabled by routing_override.yaml)
                if not instruction and not explicitly_disabled and tag_upper in registry_data:
                    instruction = str(registry_data[tag_upper].get("routing_instructions") or "").strip() or None

                if instruction:
                    merged_instructions.append(f"- [{tag_upper}] {instruction}")

            if merged_instructions:
                block = "\n### DYNAMIC ROUTING RULES ###\n"
                block += "These rules define how to choose targets or modes for specific tools. FOLLOW THEM STRICTLY.\n"
                block += "\n".join(merged_instructions) + "\n"
                return block
            return ""
        except Exception as e:
            logger.error(f"RoutingManager: Routing error: {e}")
            return ""
