"""
hecos/core/global_presets/manager.py
CRUD operations for SoulProfiles (Global Presets).
"""

import os
import glob
from typing import Dict, List, Optional
from datetime import datetime

from hecos.core.logging import logger
from hecos.core.constants import CONFIG_DATA_DIR
from hecos.config import load_yaml, save_yaml
from hecos.core.global_presets.schema import SoulProfile, SoulMeta

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

def delete_soul(soul_id: str) -> bool:
    """Deletes a SoulProfile from disk."""
    _ensure_dir()
    filepath = os.path.join(GLOBAL_PRESETS_DIR, f"{soul_id}.global_preset.yaml")
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
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
        if hasattr(sys, "hecos_config_manager"):
            cfg = sys.hecos_config_manager.config.get("ai", {})
            return cfg.get("active_global_preset")
    except Exception as e:
        logger.error(f"[GlobalPresets] Error getting active soul for session {session_id}: {e}")
    return None
    
def get_active_soul(session_id: str) -> Optional[SoulProfile]:
    """Returns the full active SoulProfile for the given session."""
    soul_id = get_active_soul_id(session_id)
    if soul_id:
        return get_soul(soul_id)
    return None
