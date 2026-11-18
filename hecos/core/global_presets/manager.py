"""
hecos/core/global_presets/manager.py
CRUD operations for SoulProfiles (Global Presets).
"""

import os
import re
import glob
from typing import List, Optional
from datetime import datetime

from hecos.core.logging import logger
from hecos.core.constants import CONFIG_DATA_DIR
from hecos.config import load_yaml, save_yaml
from hecos.core.global_presets.schema import SoulProfile

GLOBAL_PRESETS_DIR = os.path.join(CONFIG_DATA_DIR, "global_presets")

def _ensure_dir():
    os.makedirs(GLOBAL_PRESETS_DIR, exist_ok=True)

def list_souls() -> List[SoulProfile]:
    """Returns a list of all available SoulProfiles."""
    _ensure_dir()
    souls = []
    for filepath in glob.glob(os.path.join(GLOBAL_PRESETS_DIR, "*.global_preset.yaml")):
        try:
            soul = load_yaml(filepath, SoulProfile)
            if soul.meta.id:
                souls.append(soul)
        except Exception as e:
            logger.warning(f"[GlobalPresets] Error loading soul at {filepath}: {e}")
    return souls

def get_soul(soul_id: str) -> Optional[SoulProfile]:
    """Gets a specific SoulProfile by its ID."""
    _ensure_dir()
    filepath = os.path.join(GLOBAL_PRESETS_DIR, f"{soul_id}.global_preset.yaml")
    if os.path.exists(filepath):
        try:
            return load_yaml(filepath, SoulProfile)
        except Exception as e:
            logger.error(f"[GlobalPresets] Error loading soul {soul_id}: {e}")
    return None

def save_soul(soul: SoulProfile) -> bool:
    """Saves a SoulProfile to disk."""
    _ensure_dir()
    if not soul.meta.id:
        return False
        
    soul.meta.updated_at = datetime.utcnow().isoformat()
    if not soul.meta.created_at:
        soul.meta.created_at = soul.meta.updated_at
        
    filepath = os.path.join(GLOBAL_PRESETS_DIR, f"{soul.meta.id}.global_preset.yaml")
    return save_yaml(filepath, soul)

def duplicate_soul(
    source_soul_id: str,
    new_name: Optional[str] = None,
    new_id: Optional[str] = None,
) -> Optional[SoulProfile]:
    """Creates and saves a deep copy of an existing SoulProfile under a unique ID."""
    source = get_soul(source_soul_id)
    if not source:
        return None

    target_name = (new_name or f"{source.meta.name} (Copy)").strip()
    if not target_name:
        target_name = f"{source.meta.name} (Copy)"

    raw_base = (new_id or target_name).lower()
    base_id = re.sub(r"[^a-z0-9]+", "_", raw_base).strip("_") or f"{source_soul_id}_copy"

    # Guarantee unique ID on disk so duplication never overwrites an existing preset
    existing_ids = {s.meta.id for s in list_souls()}
    candidate_id = base_id
    suffix = 2
    while candidate_id in existing_ids:
        candidate_id = f"{base_id}_{suffix}"
        suffix += 1

    cloned = source.model_copy(deep=True)
    cloned.meta.id = candidate_id
    cloned.meta.name = target_name
    cloned.meta.created_at = ""
    cloned.meta.updated_at = ""

    if save_soul(cloned):
        return cloned
    return None

def delete_soul(soul_id: str) -> bool:
    """Deletes a SoulProfile from disk."""
    _ensure_dir()
    filepath = os.path.join(GLOBAL_PRESETS_DIR, f"{soul_id}.global_preset.yaml")
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
            from .usage_stats import delete_preset_usage
            delete_preset_usage(soul_id)
            return True
        except Exception as e:
            logger.error(f"[GlobalPresets] Error deleting soul {soul_id}: {e}")
    return False

def get_active_soul_id(session_id: str) -> Optional[str]:
    """
    Returns the ID of the active Global Preset (Soul) for the given session.
    Reads from the session_config_db, falling back to the global system config.
    """
    try:
        if session_id and session_id != "global":
            from hecos.memory.session_config_db import get_session_config
            config_override = get_session_config(session_id)
            if config_override and isinstance(config_override, dict):
                sid = config_override.get('active_global_preset')
                if sid:
                    return sid
        
        # Fallback to global
        import sys
        if hasattr(sys, "hecos_config_manager") and sys.hecos_config_manager:
            cfg = sys.hecos_config_manager.config.get("ai", {})
            val = cfg.get("active_global_preset")
            if val:
                return val
        
        # Direct file fallback if config manager is not in sys
        try:
            sys_yaml = os.path.join(CONFIG_DATA_DIR, "system.yaml")
            if os.path.exists(sys_yaml):
                import yaml
                with open(sys_yaml, "r", encoding="utf-8") as _f:
                    data = yaml.safe_load(_f) or {}
                return data.get("ai", {}).get("active_global_preset")
        except Exception:
            pass
    except Exception as e:
        logger.error(f"[GlobalPresets] Error getting active soul for session {session_id}: {e}")
    return None
    
def get_active_soul(session_id: str) -> Optional[SoulProfile]:
    """Returns the full active SoulProfile for the given session."""
    soul_id = get_active_soul_id(session_id)
    if soul_id:
        return get_soul(soul_id)
    return None


# Canonical Preset Manager function aliases
list_presets = list_souls
get_preset = get_soul
save_preset = save_soul
duplicate_preset = duplicate_soul
delete_preset = delete_soul
get_active_preset_id = get_active_soul_id
get_active_preset = get_active_soul
