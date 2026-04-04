"""
MODULE: YAML Config Utilities
DESCRIPTION: Shared helpers to load, save and migrate configuration files
             from/to YAML with Pydantic v2 validation.
"""

from __future__ import annotations

import os
import json
import shutil
from typing import Any, Dict, Optional, Type, TypeVar

import yaml
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


# ──────────────────────────────────────────────────────────────────────────────
# INTERNAL HELPERS
# ──────────────────────────────────────────────────────────────────────────────

def _deep_merge(base: dict, patch: dict) -> dict:
    """
    Merge *patch* into *base* recursively.
    Keys in *patch* that are dicts are merged with the corresponding key in
    *base* (if it is also a dict); otherwise the value is overwritten.
    Returns *base* (mutated in place).
    """
    for k, v in patch.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v
    return base


# ──────────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ──────────────────────────────────────────────────────────────────────────────

def load_yaml(path: str, schema_cls: Type[T], *, auto_migrate_json: bool = True) -> T:
    """
    Load a YAML config file and validate it against *schema_cls*.

    - If the YAML file exists: parse it, deep-merge with schema defaults, return model.
    - If the YAML is missing but a matching .json exists: auto-migrate.
    - If neither exists: return schema defaults and write the YAML immediately.

    Args:
        path: Absolute or relative path to the .yaml file.
        schema_cls: Pydantic BaseModel subclass to validate against.
        auto_migrate_json: If True, look for a .json sibling and migrate it.

    Returns:
        An instance of *schema_cls* with the loaded (or default) values.
    """
    if not os.path.isabs(path):
        path = os.path.abspath(path)

    # Try auto-migration from JSON if YAML not found
    if auto_migrate_json and not os.path.exists(path):
        json_path = path.replace(".yaml", ".json")
        if os.path.exists(json_path):
            migrate_json_to_yaml(json_path, path, schema_cls)

    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw: dict = yaml.safe_load(f) or {}

            # Start from schema defaults, then overlay with what's in the file
            defaults = schema_cls().model_dump()
            merged = _deep_merge(defaults, raw)
            return schema_cls.model_validate(merged)
        except Exception as e:
            print(f"[YAML-UTILS] Warning: could not load {path}: {e}. Using defaults.")

    # Fallback: write defaults and return
    model = schema_cls()
    save_yaml(path, model)
    return model


def save_yaml(path: str, model: BaseModel) -> bool:
    """
    Serialize a Pydantic model to YAML and write it to *path*.

    Args:
        path: Destination .yaml file path.
        model: Pydantic model instance to serialize.

    Returns:
        True on success, False on error.
    """
    if not os.path.isabs(path):
        path = os.path.abspath(path)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        data = model.model_dump()
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        return True
    except Exception as e:
        print(f"[YAML-UTILS] Error saving {path}: {e}")
        return False


def migrate_json_to_yaml(json_path: str, yaml_path: str, schema_cls: Type[T]) -> Optional[T]:
    """
    One-shot migration: read a JSON file, validate with *schema_cls*, write YAML,
    and rename the original JSON to *.json.bak* (so data is never lost).

    Args:
        json_path: Source .json file.
        yaml_path: Destination .yaml file.
        schema_cls: Pydantic model to validate against.

    Returns:
        The loaded model on success, None on failure.
    """
    if not os.path.exists(json_path):
        return None
    if os.path.exists(yaml_path):
        return None  # Already migrated

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            raw: dict = json.load(f)

        defaults = schema_cls().model_dump()
        merged = _deep_merge(defaults, raw)
        model = schema_cls.model_validate(merged)

        save_yaml(yaml_path, model)

        # Keep JSON as backup
        bak_path = json_path + ".bak"
        shutil.move(json_path, bak_path)

        print(f"[YAML-UTILS] Migrated {os.path.basename(json_path)} to {os.path.basename(yaml_path)}"
              f" (backup: {os.path.basename(bak_path)})")
        return model

    except Exception as e:
        print(f"[YAML-UTILS] Migration failed for {json_path}: {e}")
        return None


def load_dict_from_yaml(path: str) -> Dict[str, Any]:
    """
    Raw YAML loader — returns a plain dict (no Pydantic validation).
    Useful for ad-hoc access without a full schema.
    """
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        print(f"[YAML-UTILS] Error reading {path}: {e}")
        return {}
