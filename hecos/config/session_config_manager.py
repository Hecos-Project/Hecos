"""
hecos/config/session_config_manager.py
Merges the global config with the active session overrides.

Architecture:
    Global Config (system.yaml)
        → Soul Profile merge (from Global Default or Chat Override preset)
            → Session DB overrides (per-chat manual tweaks)

The soul profile is ALWAYS applied dynamically at inference time,
even for brand-new sessions with no per-session overrides.
This ensures Global Default presets (model, voice, persona, inference params)
are consistently enforced without relying on stale values in system.yaml/audio.yaml.
"""
from hecos.memory.session_config_db import get_session_config
from hecos.core.logging import logger
import copy


def _deep_merge(dict1: dict, dict2: dict):
    """Recursively merge dict2 into dict1 (mutates dict1)."""
    for k, v in dict2.items():
        if k in dict1 and isinstance(dict1[k], dict) and isinstance(v, dict):
            _deep_merge(dict1[k], v)
        else:
            dict1[k] = v


def merge_session_config(global_config: dict, session_id: str) -> dict:
    """
    Returns a deep copy of the global config, merged with:
    1. The active Soul Profile (Global Default or session-specific preset)
    2. Any per-session overrides from the session config DB
    """
    if not session_id or not global_config:
        return global_config

    merged = copy.deepcopy(global_config)

    # ── 1. Merge Active Soul Profile (always, even without session overrides) ──
    try:
        from hecos.core.global_presets import get_active_soul, merge_soul_into_config
        active_soul = get_active_soul(session_id)
        if active_soul:
            logger.debug(f"[SESSION_CONFIG] Applying soul '{active_soul.meta.name}' for session {session_id}")
            merged = merge_soul_into_config(merged, active_soul)
    except Exception as e:
        logger.error(f"[SESSION_CONFIG] Error merging soul for session {session_id}: {e}")

    # ── 2. Apply per-session overrides on top (if any) ──
    overrides = get_session_config(session_id)
    if overrides:
        logger.debug(f"[SESSION_CONFIG] Applying {len(overrides)} session override keys for {session_id}")
        _deep_merge(merged, overrides)

    return merged
