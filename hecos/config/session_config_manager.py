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
    """Recursively merge dict2 into dict1 (mutates dict1).
    Skips keys where dict2 has None, so empty overrides never erase valid base/soul settings.
    """
    for k, v in dict2.items():
        if v is None:
            continue
        if isinstance(v, dict):
            if k not in dict1 or not isinstance(dict1[k], dict):
                dict1[k] = {}
            _deep_merge(dict1[k], v)
        else:
            dict1[k] = v


def merge_session_config(global_config: dict, session_id: str = None) -> dict:
    """
    Returns a deep copy of the global config, merged with:
    1. The active Soul Profile (Global Default or session-specific preset)
    2. Any per-session overrides from the session config DB
    """
    if not global_config:
        return global_config

    merged = copy.deepcopy(global_config)

    # ── 1. Merge Active Soul Profile (always, even without session overrides or if session_id is None) ──
    try:
        from hecos.core.global_presets import get_active_soul, merge_soul_into_config
        target_sid = session_id or "global"
        active_soul = get_active_soul(target_sid)
        if active_soul:
            logger.debug(f"[SESSION_CONFIG] Applying soul '{active_soul.meta.name}' for session {target_sid}")
            merged = merge_soul_into_config(merged, active_soul)
    except Exception as e:
        logger.error(f"[SESSION_CONFIG] Error merging soul for session {session_id}: {e}")

    # ── 2. Apply per-session overrides on top (if any) ──
    if session_id:
        overrides = get_session_config(session_id)
        if overrides:
            logger.debug(f"[SESSION_CONFIG] Applying {len(overrides)} session override keys for {session_id}")
            _deep_merge(merged, overrides)

            # Map legacy or UI 'model' overrides into 'backend' if present
            model_ov = overrides.get('model')
            if isinstance(model_ov, dict):
                btype = model_ov.get('backend_type')
                if btype:
                    if 'backend' not in merged:
                        merged['backend'] = {}
                    merged['backend']['type'] = btype
                    mname = model_ov.get('model_name')
                    if mname:
                        if btype not in merged['backend']:
                            merged['backend'][btype] = {}
                        merged['backend'][btype]['model'] = mname

    return merged
