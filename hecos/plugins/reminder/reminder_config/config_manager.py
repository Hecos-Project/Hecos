"""
reminder package — Config Manager (Autonomous TOML)
Reads/writes the package's own reminder.toml without touching Hecos core config.

File locations after HPM install:
  hecos/plugins/reminder/reminder_config/defaults.toml  ← read-only factory defaults
  hecos/plugins/reminder/reminder_config/reminder.toml  ← user config (created at first run)
"""
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore

try:
    import tomli_w
    _HAS_TOMLI_W = True
except ImportError:
    _HAS_TOMLI_W = False

try:
    from hecos.core.logging import logger
except ImportError:
    class _L:
        def info(self, *a):    print("[REMINDER CONFIG]", *a)
        def error(self, *a):   print("[REMINDER CONFIG ERR]", *a)
        def warning(self, *a): print("[REMINDER CONFIG WARN]", *a)
    logger = _L()

# ── Path resolution ────────────────────────────────────────────────────────────
_THIS_DIR    = Path(__file__).parent.resolve()
_DEFAULTS    = _THIS_DIR / "defaults.toml"
_CONFIG_FILE = _THIS_DIR / "reminder.toml"


def _load_defaults() -> dict:
    """Load the shipped defaults.toml."""
    try:
        return tomllib.loads(_DEFAULTS.read_bytes().decode("utf-8"))
    except Exception as e:
        logger.error(f"[REMINDER] Could not load defaults: {e}")
        return {"reminder": {}}


def get_config() -> dict:
    """
    Returns the full reminder config dict.
    If reminder.toml doesn't exist yet, creates it from defaults.
    """
    if not _CONFIG_FILE.exists():
        _create_from_defaults()

    try:
        return tomllib.loads(_CONFIG_FILE.read_bytes().decode("utf-8"))
    except Exception as e:
        logger.error(f"[REMINDER] Failed to read config: {e}")
        return _load_defaults()


def get_reminder_config() -> dict:
    """Returns just the [reminder] section."""
    return get_config().get("reminder", {})


def save_config(data: dict) -> bool:
    """
    Saves the full config dict to reminder.toml.
    data must include the top-level [reminder] key.
    """
    if not _HAS_TOMLI_W:
        logger.error("[REMINDER] tomli_w not installed. Cannot save config. Run: pip install tomli_w")
        return False
    try:
        _CONFIG_FILE.write_bytes(tomli_w.dumps(data).encode("utf-8"))
        logger.info("[REMINDER] Config saved.")
        return True
    except Exception as e:
        logger.error(f"[REMINDER] Failed to save config: {e}")
        return False


def save_reminder_section(section: dict) -> bool:
    """
    Saves just the [reminder] section, merging with existing config.
    """
    cfg = get_config()
    existing = cfg.get("reminder", {})
    existing.update(section)
    cfg["reminder"] = existing
    return save_config(cfg)


def _create_from_defaults():
    """Copy defaults.toml content to reminder.toml on first run."""
    try:
        defaults = _load_defaults()
        save_config(defaults)
        logger.info("[REMINDER] Created reminder.toml from defaults.")
    except Exception as e:
        logger.error(f"[REMINDER] Could not create config from defaults: {e}")
