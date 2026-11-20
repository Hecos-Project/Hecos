"""
hecos/core/action_plans/config.py
Configuration loader, validator, and saver for the shared Action Plans Core module.
Reads and persists under `plugins.ACTION_PLANS` cleanly without schema conflicts.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, Optional

from hecos.core.action_plans.models import PLAN_MODES

DEFAULT_ACTION_PLANS_CONFIG: Dict[str, Any] = {
    "enabled": True,
    "lazy_load": False,
    "llm_callable": True,
    "plan_mode": "auto",  # "auto" | "confirm" | "manual" | "off"
    "auto_plan_min_steps_hint": 3,
    "expose_tools_in_custom_presets": True,
    "checkpoint_enabled": True,
    "resume_banner_enabled": True,
    "resume_extra_steps": 10,
    "retention_days": 14,
    "flows_checkpoint_enabled": True,
    "approval_timeout_seconds": 300,
}


def normalize_action_plans_config(raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Merge partial settings onto safe typed defaults with bounded numeric clamps."""
    merged = copy.deepcopy(DEFAULT_ACTION_PLANS_CONFIG)
    if not isinstance(raw, dict):
        return merged

    for bool_key in (
        "enabled",
        "lazy_load",
        "llm_callable",
        "expose_tools_in_custom_presets",
        "checkpoint_enabled",
        "resume_banner_enabled",
        "flows_checkpoint_enabled",
    ):
        if bool_key in raw and raw[bool_key] is not None:
            merged[bool_key] = bool(raw[bool_key])

    mode = str(raw.get("plan_mode") or merged["plan_mode"]).strip().lower()
    merged["plan_mode"] = mode if mode in PLAN_MODES else "auto"

    def _clamp_int(key: str, low: int, high: int, fallback: int) -> int:
        try:
            return max(low, min(high, int(raw.get(key, fallback))))
        except Exception:
            return fallback

    merged["auto_plan_min_steps_hint"] = _clamp_int("auto_plan_min_steps_hint", 2, 20, 3)
    merged["resume_extra_steps"] = _clamp_int("resume_extra_steps", 1, 50, 10)
    merged["retention_days"] = _clamp_int("retention_days", 0, 365, 14)
    merged["approval_timeout_seconds"] = _clamp_int("approval_timeout_seconds", 30, 1800, 300)
    return merged


def _resolve_cfg_mgr(explicit_cfg_mgr: Any = None) -> Any:
    if explicit_cfg_mgr is not None:
        return explicit_cfg_mgr
    import sys
    sys_mgr = getattr(sys, "hecos_config_manager", None)
    if sys_mgr is not None:
        return sys_mgr
    try:
        from hecos.app.config import ConfigManager
        return ConfigManager()
    except Exception:
        return None


def get_action_plans_config(cfg_mgr: Any = None, raw_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Return normalized runtime config for `plugins.ACTION_PLANS`."""
    raw_block: Optional[Dict[str, Any]] = None
    if isinstance(raw_config, dict):
        candidate = (raw_config.get("plugins") or {}).get("ACTION_PLANS")
        if isinstance(candidate, dict):
            raw_block = candidate

    if raw_block is None:
        mgr = _resolve_cfg_mgr(cfg_mgr)
        if mgr is not None:
            try:
                cfg_dict = getattr(mgr, "config", None) or {}
                candidate = (cfg_dict.get("plugins") or {}).get("ACTION_PLANS")
                if isinstance(candidate, dict):
                    raw_block = candidate
            except Exception:
                raw_block = None

    return normalize_action_plans_config(raw_block)


def save_action_plans_config(updates: Dict[str, Any], cfg_mgr: Any = None) -> Dict[str, Any]:
    """Validate, merge, and persist `plugins.ACTION_PLANS` settings via ConfigManager."""
    current = get_action_plans_config(cfg_mgr=cfg_mgr)
    combined = {**current, **(updates or {})}
    clean = normalize_action_plans_config(combined)

    mgr = _resolve_cfg_mgr(cfg_mgr)
    if mgr is not None and hasattr(mgr, "config"):
        mgr.config.setdefault("plugins", {})
        existing = mgr.config["plugins"].get("ACTION_PLANS")
        if isinstance(existing, dict):
            existing.update(clean)
        else:
            mgr.config["plugins"]["ACTION_PLANS"] = dict(clean)
        if hasattr(mgr, "save_config"):
            mgr.save_config()
    return clean
