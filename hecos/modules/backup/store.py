"""
MODULE: Backup Store
DESCRIPTION: Persistent configuration for the Global Backup Orchestrator.
             Reads/writes backup_config.yaml in hecos/config/data/.
"""

import os
import json
import threading
from hecos.core.logging import logger

_lock = threading.Lock()

_DEFAULT_CONFIG = {
    "enabled": False,
    "schedule_preset": "daily_2am",   # preset key
    "schedule_cron": "0 2 * * *",     # raw cron (kept in sync)
    "destination": "",
    "keep_last": 7,
    "last_backup": None,              # ISO datetime string
    "last_result": None,              # "ok" | "error" | None
    "modules": {
        "calendar":  True,
        "chat":      True,
        "memory":    True,
        "reminders": True,
        "contacts":  True,
        "flows":     True,
        "users":     True,
        "lists":     True,
        "system_config": True,
    }
}

# Preset schedules — shown as dropdown in the UI
SCHEDULE_PRESETS = {
    "every_6h":    {"label": "backup_preset_6h",    "cron": "0 */6 * * *"},
    "every_12h":   {"label": "backup_preset_12h",   "cron": "0 */12 * * *"},
    "daily_2am":   {"label": "backup_preset_daily",  "cron": "0 2 * * *"},
    "weekly_sun":  {"label": "backup_preset_weekly", "cron": "0 3 * * 0"},
    "custom":      {"label": "backup_preset_custom", "cron": ""},
}


def _get_config_path() -> str:
    """Resolve path to backup_config.json relative to this file."""
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(root, "config", "data", "backup_config.json")


def load() -> dict:
    """Load backup config from disk. Dynamically merges HPM backup modules. Returns default if missing/corrupt."""
    path = _get_config_path()
    with _lock:
        if not os.path.exists(path):
            cfg = dict(_DEFAULT_CONFIG)
            cfg["modules"] = dict(_DEFAULT_CONFIG["modules"])
        else:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                cfg = dict(_DEFAULT_CONFIG)
                cfg.update(data)
                if "modules" not in cfg:
                    cfg["modules"] = dict(_DEFAULT_CONFIG["modules"])
                else:
                    for k, v in _DEFAULT_CONFIG["modules"].items():
                        cfg["modules"].setdefault(k, v)
            except Exception as e:
                logger.warning("BACKUP", f"Could not load backup_config.json: {e}")
                cfg = dict(_DEFAULT_CONFIG)
                cfg["modules"] = dict(_DEFAULT_CONFIG["modules"])

    # Discover dynamic HPM packages with [backup] capabilities
    try:
        import tomllib
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        hpm_dir = os.path.join(root, "hpm")
        if os.path.isdir(hpm_dir):
            installed_hpm = set()
            for d in os.listdir(hpm_dir):
                mf_path = os.path.join(hpm_dir, d, "hpkg_manifest.toml")
                if os.path.exists(mf_path):
                    try:
                        with open(mf_path, "rb") as f:
                            mf_data = tomllib.load(f)
                        pkg_id = mf_data.get("id", d)
                        installed_hpm.add(pkg_id)
                        if "backup" in mf_data and mf_data["backup"].get("enabled"):
                            # Add to config modules if not present (default True)
                            cfg["modules"].setdefault(pkg_id, True)
                    except Exception as pe:
                        logger.warning("BACKUP", f"Error parsing manifest for {d}: {pe}")
            
            # Optionally clean up removed HPM packages from config
            to_remove = []
            for k in cfg["modules"].keys():
                if k not in _DEFAULT_CONFIG["modules"] and k not in installed_hpm:
                    to_remove.append(k)
            for k in to_remove:
                cfg["modules"].pop(k)

    except Exception as e:
        logger.error(f"[BACKUP] Error discovering HPM packages: {e}")

    return cfg


def save(cfg: dict) -> bool:
    """Persist backup config to disk."""
    path = _get_config_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with _lock:
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"[BACKUP] Could not save backup_config.json: {e}")
            return False


def update_last_run(result: str, timestamp: str) -> None:
    """Update last_backup and last_result fields atomically."""
    cfg = load()
    cfg["last_backup"] = timestamp
    cfg["last_result"] = result
    save(cfg)


def get_cron_for_preset(preset_key: str, custom_cron: str = "") -> str:
    """Return the cron expression for a given preset key."""
    if preset_key == "custom":
        return custom_cron
    return SCHEDULE_PRESETS.get(preset_key, SCHEDULE_PRESETS["daily_2am"])["cron"]
