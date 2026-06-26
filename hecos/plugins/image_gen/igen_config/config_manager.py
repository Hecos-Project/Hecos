"""
image_gen package — Config Manager (Autonomous TOML)
Reads/writes the package's own image_gen.toml without touching Hecos core config.
"""
import os
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib

try:
    import tomli_w
    _HAS_TOMLI_W = True
except ImportError:
    _HAS_TOMLI_W = False

try:
    from hecos.core.logging import logger
except ImportError:
    class _L:
        def info(self, *a): print("[IMAGE_GEN CONFIG]", *a)
        def error(self, *a): print("[IMAGE_GEN CONFIG ERR]", *a)
        def warning(self, *a): print("[IMAGE_GEN CONFIG WARN]", *a)
    logger = _L()

# ── Path resolution ────────────────────────────────────────────────────────────
# When installed by HPM, the package lives in:
#   hecos/packages/image_gen/   (installed_dir)
# This file is at: image_gen_src/config/config_manager.py
# After install: hecos/packages/image_gen/config/config_manager.py

_THIS_DIR = Path(__file__).parent.resolve()
_DEFAULTS_FILE = _THIS_DIR / "defaults.toml"
_CONFIG_FILE   = _THIS_DIR / "image_gen.toml"


def _load_defaults() -> dict:
    """Load the shipped defaults.toml."""
    try:
        return tomllib.loads(_DEFAULTS_FILE.read_bytes().decode("utf-8"))
    except Exception as e:
        logger.error(f"[IMAGE_GEN] Could not load defaults: {e}")
        return {"image_gen": {}}


def get_config() -> dict:
    """
    Returns the full image_gen config dict.
    If image_gen.toml doesn't exist yet, creates it from defaults.
    """
    if not _CONFIG_FILE.exists():
        _migrate_or_create_from_defaults()

    try:
        raw = tomllib.loads(_CONFIG_FILE.read_bytes().decode("utf-8"))
        return raw
    except Exception as e:
        logger.error(f"[IMAGE_GEN] Failed to read config: {e}")
        return _load_defaults()


def get_image_gen_config() -> dict:
    """Returns just the [image_gen] section."""
    return get_config().get("image_gen", {})


def save_config(data: dict) -> bool:
    """
    Saves the full config dict to image_gen.toml.
    data should be the full dict (including top-level [image_gen] key).
    """
    if not _HAS_TOMLI_W:
        logger.error("[IMAGE_GEN] tomli_w not installed. Cannot save config. Run: pip install tomli_w")
        return False
    try:
        toml_bytes = tomli_w.dumps(data).encode("utf-8")
        _CONFIG_FILE.write_bytes(toml_bytes)
        logger.info("[IMAGE_GEN] Config saved.")
        return True
    except Exception as e:
        logger.error(f"[IMAGE_GEN] Failed to save config: {e}")
        return False


def save_image_gen_section(section: dict) -> bool:
    """
    Saves just the [image_gen] section, merging with existing config.
    """
    cfg = get_config()
    existing = cfg.get("image_gen", {})
    existing.update(section)
    cfg["image_gen"] = existing
    return save_config(cfg)


def _migrate_or_create_from_defaults():
    """
    Try to migrate from hecos/config/data/media.yaml if it exists.
    Otherwise copy defaults.toml to image_gen.toml.
    """
    migrated = _try_migrate_from_yaml()
    if not migrated:
        _create_from_defaults()


def _try_migrate_from_yaml() -> bool:
    """Attempt to read hecos/config/data/media.yaml and import image_gen section."""
    try:
        # Try to locate the old media.yaml relative to the Hecos root
        import yaml
        hecos_root = _THIS_DIR.parent.parent.parent.parent  # packages/image_gen/config -> hecos -> root
        yaml_path = hecos_root / "hecos" / "config" / "data" / "media.yaml"
        if not yaml_path.exists():
            return False

        with open(yaml_path, "r", encoding="utf-8") as f:
            media_data = yaml.safe_load(f)

        if not media_data or "image_gen" not in media_data:
            return False

        igen = media_data["image_gen"]
        # Convert None values to TOML-safe equivalents
        for k, v in list(igen.items()):
            if v is None:
                igen[k] = ""

        logger.info("[IMAGE_GEN] Migrating configuration from media.yaml → image_gen.toml")
        return save_config({"image_gen": igen})

    except Exception as e:
        logger.warning(f"[IMAGE_GEN] YAML migration failed (non-critical): {e}")
        return False


def _create_from_defaults():
    """Copy defaults.toml content to image_gen.toml."""
    try:
        defaults = _load_defaults()
        save_config(defaults)
        logger.info("[IMAGE_GEN] Created image_gen.toml from defaults.")
    except Exception as e:
        logger.error(f"[IMAGE_GEN] Could not create config from defaults: {e}")
