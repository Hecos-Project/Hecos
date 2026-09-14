"""
hecos/config/session_config_manager.py
Merges the global config with the active session overrides.
"""
from hecos.memory.session_config_db import get_session_config
from hecos.core.logging import logger
import copy

def merge_session_config(global_config: dict, session_id: str) -> dict:
    """
    Returns a deep copy of the global config, merged with session_id's overrides.
    """
    if not session_id or not global_config:
        return global_config
        
    overrides = get_session_config(session_id)
    if not overrides:
        return global_config
        
    logger.debug(f"[SESSION_CONFIG] Merging overrides for session {session_id}")
    
    # Deep copy to prevent modifying the system config
    merged = copy.deepcopy(global_config)
    
    def _deep_merge(dict1, dict2):
        for k, v in dict2.items():
            if k in dict1 and isinstance(dict1[k], dict) and isinstance(v, dict):
                _deep_merge(dict1[k], v)
            else:
                dict1[k] = v
                
    _deep_merge(merged, overrides)
    return merged
