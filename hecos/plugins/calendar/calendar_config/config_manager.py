import os
from pathlib import Path
from hecos.core.logging import logger

try:
    import tomllib
except ImportError:
    import tomli as tomllib
import tomli_w

# Paths
CALENDAR_PKG_DIR = Path(__file__).parent.parent
DEFAULTS_FILE = CALENDAR_PKG_DIR / "calendar_config" / "defaults.toml"
USER_CONFIG_FILE = CALENDAR_PKG_DIR / "calendar_config" / "calendar.toml"

_cached_config = None

def get_calendar_config(force_reload=False) -> dict:
    global _cached_config
    if _cached_config and not force_reload:
        return _cached_config
    
    # 1. Load Defaults
    config = {}
    if DEFAULTS_FILE.exists():
        try:
            with open(DEFAULTS_FILE, "rb") as f:
                config = tomllib.load(f)
        except Exception as e:
            logger.error(f"[CALENDAR-CFG] Error loading defaults.toml: {e}")
            
    # 2. Load User settings and overlay
    if USER_CONFIG_FILE.exists():
        try:
            with open(USER_CONFIG_FILE, "rb") as f:
                user_cfg = tomllib.load(f)
                
            def deep_update(d, u):
                for k, v in u.items():
                    if isinstance(v, dict) and k in d and isinstance(d[k], dict):
                        deep_update(d[k], v)
                    else:
                        d[k] = v
                        
            deep_update(config, user_cfg)
        except Exception as e:
            logger.error(f"[CALENDAR-CFG] Error loading calendar.toml: {e}")
            
    _cached_config = config.get("calendar", {})
    return _cached_config

def save_calendar_config(new_settings: dict) -> bool:
    global _cached_config
    
    # We only save to calendar.toml (overrides)
    # We do a read-modify-write on user_config_file
    user_cfg = {}
    if USER_CONFIG_FILE.exists():
        try:
            with open(USER_CONFIG_FILE, "rb") as f:
                user_cfg = tomllib.load(f)
        except Exception:
            pass
            
    if "calendar" not in user_cfg:
        user_cfg["calendar"] = {}
        
    def deep_update(d, u):
        for k, v in u.items():
            if isinstance(v, dict) and k in d and isinstance(d[k], dict):
                deep_update(d[k], v)
            else:
                d[k] = v
                
    deep_update(user_cfg["calendar"], new_settings)
    
    # Write back
    USER_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(USER_CONFIG_FILE, "wb") as f:
            tomli_w.dump(user_cfg, f)
        
        # update cache
        get_calendar_config(force_reload=True)
        return True
    except Exception as e:
        logger.error(f"[CALENDAR-CFG] Error saving calendar.toml: {e}")
        return False
