import json
import os
from hecos.core.logging import logger
from hecos.core.system.module_loader import get_active_tags
from hecos.config import load_yaml

# Replicate the constants needed for routing
_HECOS_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
REGISTRY_PATH = os.path.join(_HECOS_DIR, "core", "registry.json")

class RoutingManager:
    """
    Manages the hybrid routing system:
    1. HPM Plugin Manifest / dynamic override (Default)
    2. Core Defaults (Fallback)
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
            
            # 3. Merge logic
            merged_instructions = []
            
            # --- FASE 6: HPM v2 Routing Support ---
            from hecos.core.package_manager.registry import PackageRegistry
            hpm_registry = PackageRegistry(os.path.join(_HECOS_DIR, "data"))
            
            for tag in active_tags:
                tag_upper = tag.upper()
                tag_lower = tag.lower()
                # Priority: HPM routing_override.yaml > HPM Manifest > Legacy Registry
                instruction = None
                
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
