import json
import os
from hecos.core.logging import logger
from hecos.core.system.module_loader import get_active_tags
from hecos.config import load_yaml
from hecos.config.schemas.routing_schema import RoutingOverrides

# Replicate the constants needed for routing
_HECOS_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
REGISTRY_PATH = os.path.join(_HECOS_DIR, "core", "registry.json")
ROUTING_OVERRIDES_PATH = os.path.join(_HECOS_DIR, "config", "data", "routing_overrides.yaml")

class RoutingManager:
    """
    Manages the 3-tier hybrid routing system:
    1. Plugin Manifest (Default)
    2. User Overrides (YAML)
    3. Core Defaults (Fallback)
    """
    @staticmethod
    def get_dynamic_instructions(config):
        try:
            # 1. Load active plugin tags
            active_tags = get_active_tags()
            
            # 2. Load instructions from registry
            registry_data = {}
            if os.path.exists(REGISTRY_PATH):
                with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
                    registry_data = json.load(f)
            
            # 3. Load user overrides
            overrides = {}
            if os.path.exists(ROUTING_OVERRIDES_PATH):
                try:
                    overrides_model = load_yaml(ROUTING_OVERRIDES_PATH, RoutingOverrides)
                    overrides = overrides_model.overrides
                except Exception as e:
                    logger.debug(f"RoutingManager: Error loading routing overrides: {e}")

            # 4. Merge logic
            merged_instructions = []
            
            # --- FASE 6: HPM v2 Routing Support ---
            from hecos.core.package_manager.registry import PackageRegistry
            hpm_registry = PackageRegistry(os.path.join(_HECOS_DIR, "data"))
            
            for tag in active_tags:
                tag_upper = tag.upper()
                tag_lower = tag.lower()
                # Priority: YAML Override > HPM routing_override.txt > HPM Manifest > Legacy Registry
                instruction = overrides.get(tag_upper)
                
                # Check HPM package
                if not instruction:
                    pkg = hpm_registry.get(tag_lower)
                    if pkg and pkg.get("install_path"):
                        # Check dynamic override file in package root
                        dyn_file = os.path.join(pkg["install_path"], "routing_override.yaml")
                        if os.path.exists(dyn_file):
                            try:
                                import yaml
                                with open(dyn_file, "r", encoding="utf-8") as df:
                                    y_data = yaml.safe_load(df)
                                    if y_data and isinstance(y_data, dict) and y_data.get("enabled", True):
                                        instruction = y_data.get("instruction", "").strip()
                            except Exception:
                                pass
                        
                        # Fallback to manifest default
                        if not instruction and pkg.get("manifest_snapshot"):
                            try:
                                snap = json.loads(pkg["manifest_snapshot"])
                                if "routing" in snap and "instructions" in snap["routing"]:
                                    instruction = snap["routing"]["instructions"]
                            except Exception:
                                pass
                
                # Fallback to legacy registry
                if not instruction and tag_upper in registry_data:
                    instruction = registry_data[tag_upper].get("routing_instructions")
                
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
