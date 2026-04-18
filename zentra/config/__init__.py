"""
MODULE: YAML Config Utilities
DESCRIPTION: Shared helpers to load, save and migrate configuration files
             from/to YAML with Pydantic v2 validation. Ensures comments are preserved.
"""

from __future__ import annotations

import os
import json
import shutil
import logging
from typing import Any, Dict, Optional, Type, TypeVar

# Logger configuration
logger = logging.getLogger("zentra.config")

try:
    import ruamel.yaml
    from ruamel.yaml import YAML
    HAS_RUAMEL = True
except ImportError:
    HAS_RUAMEL = False

import yaml
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# INTERNAL HELPERS
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

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


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# PUBLIC API
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def load_yaml(path: str, schema_cls: Type[T], *, auto_migrate_json: bool = True) -> T:
    """
    Load a YAML config file and validate it against *schema_cls*.
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
                if HAS_RUAMEL:
                    ryaml = YAML()
                    raw: dict = ryaml.load(f) or {}
                else:
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
    Uses ruamel.yaml to preserve comments if available.
    """
    if not os.path.isabs(path):
        path = os.path.abspath(path)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        new_data = model.model_dump()
        
        if HAS_RUAMEL:
            ryaml = YAML()
            ryaml.preserve_quotes = True
            ryaml.indent(mapping=2, sequence=4, offset=2)
            
            if os.path.exists(path) and "system.yaml" not in path.lower():
                with open(path, "r", encoding="utf-8") as f:
                    data = ryaml.load(f) or {}
                if not isinstance(data, dict):
                    data = {}
                _deep_merge(data, new_data) # Preserves CommentedMap keys
                with open(path, "w", encoding="utf-8") as f:
                    ryaml.dump(data, f)
            else:
                # Direct overwrite for system.yaml or new files to avoid merge bugs
                with open(path, "w", encoding="utf-8") as f:
                    ryaml.dump(new_data, f)
            return True
        else:
            with open(path, "w", encoding="utf-8") as f:
                yaml.dump(new_data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
            return True
    except Exception as e:
        import traceback
        logger.error(f"[YAML-UTILS] CRITICAL ERROR saving {path}: {e}")
        logger.error(traceback.format_exc())
        return False


def migrate_json_to_yaml(json_path: str, yaml_path: str, schema_cls: Type[T]) -> Optional[T]:
    if not os.path.exists(json_path):
        return None
    if os.path.exists(yaml_path):
        return None

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            raw: dict = json.load(f)

        defaults = schema_cls().model_dump()
        merged = _deep_merge(defaults, raw)
        model = schema_cls.model_validate(merged)

        save_yaml(yaml_path, model)

        bak_path = json_path + ".bak"
        shutil.move(json_path, bak_path)

        print(f"[YAML-UTILS] Migrated {os.path.basename(json_path)} to {os.path.basename(yaml_path)}")
        return model

    except Exception as e:
        print(f"[YAML-UTILS] Migration failed for {json_path}: {e}")
        return None


def load_dict_from_yaml(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            if HAS_RUAMEL:
                ryaml = YAML()
                return ryaml.load(f) or {}
            else:
                return yaml.safe_load(f) or {}
    except Exception as e:
        print(f"[YAML-UTILS] Error reading {path}: {e}")
        return {}
