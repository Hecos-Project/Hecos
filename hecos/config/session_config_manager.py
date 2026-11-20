"""
hecos/config/session_config_manager.py
Merges the global config with the active session overrides and live Soul Forge draft.

Architecture:
    Global Config (system.yaml)
        → Soul Profile merge (from Session Preset or Global Default preset)
            → Session Draft Soul merge (persona, model, inference, voice, payload)
                → Session DB raw overrides (per-chat topbar / slash-command tweaks)
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


def _apply_soul_dict(merged: dict, soul_dict: dict) -> dict:
    """Validate a partial or full Soul-shaped dict and merge it via merge_soul_into_config."""
    if not soul_dict or not isinstance(soul_dict, dict):
        return merged
    soul_keys = ('persona', 'model', 'inference', 'voice', 'payload')
    if not any(k in soul_dict and soul_dict[k] for k in soul_keys):
        return merged
    try:
        from hecos.core.global_presets.schema import SoulProfile
        from hecos.core.global_presets.merger import merge_soul_into_config
        payload_data = {k: soul_dict[k] for k in soul_keys if k in soul_dict and isinstance(soul_dict[k], dict)}
        if not payload_data:
            return merged
        payload_data['meta'] = soul_dict.get('meta') or {'id': '_session_draft', 'name': 'Session Draft', 'icon': '✏️'}
        draft_soul = SoulProfile.model_validate(payload_data)
        merged = merge_soul_into_config(merged, draft_soul)
    except Exception as e:
        logger.error(f"[SESSION_CONFIG] Error applying session soul draft: {e}")
    return merged


def merge_session_config(global_config: dict, session_id: str = None, extra_draft: dict = None) -> dict:
    """
    Returns a deep copy of the global config, merged with:
    1. The active Soul Profile (Global Default or session-specific preset)
    2. Any per-session overrides / Soul Forge draft from the session config DB
    3. Optional in-memory extra_draft (used by Quick Test Lab without persisting)
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

    # ── 2. Apply per-session overrides / draft on top (if any) ──
    if session_id:
        overrides = get_session_config(session_id)
        if overrides and isinstance(overrides, dict):
            logger.debug(f"[SESSION_CONFIG] Applying {len(overrides)} session override keys for {session_id}")
            
            # 2a. Apply raw dictionary overrides (ai, backend, voice, payload_control)
            raw_subset = {
                k: v for k, v in overrides.items()
                if k in ('ai', 'backend', 'voice', 'payload_control') and v is not None
            }
            if raw_subset:
                _deep_merge(merged, raw_subset)

            # 2b. Apply Soul-shaped sections (persona, model, inference, voice, payload)
            # This properly maps inference.* -> backend.<type>.*, persona.* -> ai.*,
            # payload.* -> payload_control.*, and voice.* -> ai.voice_overrides!
            if isinstance(overrides.get('draft'), dict):
                merged = _apply_soul_dict(merged, overrides['draft'])
            merged = _apply_soul_dict(merged, overrides)

            # 2c. Re-apply explicit payload_control so slash commands (/tools, /memory, /soul) always win
            if isinstance(overrides.get('payload_control'), dict):
                _deep_merge(merged.setdefault('payload_control', {}), overrides['payload_control'])

    # ── 3. Apply optional in-memory extra_draft (e.g. Lab test) ──
    if extra_draft and isinstance(extra_draft, dict):
        merged = _apply_soul_dict(merged, extra_draft)

    return merged
