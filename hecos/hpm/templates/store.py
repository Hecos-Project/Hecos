"""
MODULE: Templates Store
DESCRIPTION: Persistent CRUD layer for message templates (email, whatsapp, telegram, discord).
             Templates are stored in hecos/data/templates.json.
             Each template keeps a full version history (last N snapshots).

Public API
──────────
  list_templates(channel)          → list[dict]
  get_template(template_id)        → dict | None
  save_template(data)              → dict          (upsert — creates or updates)
  delete_template(template_id)     → bool
  render_template(template_id, variables)  → dict  {subject, body_html, body_text}
  get_version_history(template_id) → list[dict]
  restore_version(template_id, version_index) → dict
  import_templates(templates, mode) → int
"""

from __future__ import annotations

import json
import os
import re
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from typing import Optional

from hecos.core.logging import logger

# ── Constants ──────────────────────────────────────────────────────────────────

# Path to the JSON store. Resolved at import time so it works from any CWD.
from hecos.core.system.module_state import _BASE_DIR
_DATA_DIR = os.path.join(_BASE_DIR, "data")
_STORE    = os.path.join(_DATA_DIR, "templates.json")

# How many past snapshots to keep per template
MAX_VERSIONS = 20

# Valid channel identifiers
VALID_CHANNELS = {"email", "whatsapp", "telegram", "discord"}


# ── Internal helpers ───────────────────────────────────────────────────────────

def _now_iso() -> str:
    """Return current UTC time as ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _load() -> dict:
    """Load the full templates store from disk. Returns {} on missing/invalid file."""
    if not os.path.exists(_STORE):
        return {}
    try:
        with open(_STORE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"[TEMPLATES] Could not read store: {e}")
        return {}


def _save(data: dict) -> bool:
    """Persist the full templates store to disk."""
    try:
        os.makedirs(_DATA_DIR, exist_ok=True)
        with open(_STORE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"[TEMPLATES] Could not write store: {e}")
        return False


def _snapshot(template: dict) -> dict:
    """Create a lightweight version snapshot from a template dict (excludes history)."""
    snap = {k: v for k, v in template.items() if k != "versions"}
    snap["snapshot_at"] = _now_iso()
    return snap


def _push_version(template: dict) -> None:
    """Append the current state of the template to its version history (in-place)."""
    if "versions" not in template:
        template["versions"] = []
    template["versions"].append(_snapshot(template))
    # Trim to MAX_VERSIONS, keeping the most recent ones
    if len(template["versions"]) > MAX_VERSIONS:
        template["versions"] = template["versions"][-MAX_VERSIONS:]


def _extract_variables(text: str) -> list[str]:
    """Extract all {{ var_name }} placeholders from a string, preserving order."""
    found = re.findall(r"\{\{\s*(\w+)\s*\}\}", text or "")
    seen: set[str] = set()
    result: list[str] = []
    for v in found:
        if v not in seen:
            seen.add(v)
            result.append(v)
    return result


def _interpolate(text: str, variables: dict) -> str:
    """Replace {{ key }} placeholders with values from the variables dict."""
    if not text:
        return text

    def _replace(match: re.Match) -> str:
        key = match.group(1).strip()
        return str(variables.get(key, match.group(0)))  # leave placeholder if key missing

    return re.sub(r"\{\{\s*(\w+)\s*\}\}", _replace, text)


# ── Public API ─────────────────────────────────────────────────────────────────

def list_templates(channel: Optional[str] = None) -> list[dict]:
    """
    Return all templates, optionally filtered by channel.

    :param channel: One of 'email', 'whatsapp', 'telegram', 'discord'.
                    If None, returns every template.
    :returns: List of template dicts, sorted by updated_at descending.
              Version history is excluded from list results (use get_template for full details).
    """
    store = _load()
    result = []
    for tpl in store.values():
        if channel and tpl.get("channel") != channel:
            continue
        # Strip version history from list payload (keep it lightweight)
        clean = {k: v for k, v in tpl.items() if k != "versions"}
        result.append(clean)
    result.sort(key=lambda t: t.get("updated_at", ""), reverse=True)
    return result


def get_template(template_id: str) -> Optional[dict]:
    """
    Return a single template by ID (full record including version history).

    :param template_id: The template UUID string.
    :returns: Template dict or None if not found.
    """
    store = _load()
    return store.get(template_id)


def save_template(data: dict) -> dict:
    """
    Create or update a template (upsert).

    If *data* contains an 'id' that matches an existing template, the existing
    record is updated and the old state is pushed to version history.
    If there is no 'id' (or the id doesn't match), a new template is created.

    Required fields: name, channel.
    Optional fields: subject (email only), body_html (email only), body_text,
                     description, tags.

    :param data: Template data dict.
    :returns: The saved template dict (without version history for brevity).
    :raises ValueError: If channel is invalid.
    """
    channel = data.get("channel", "")
    if channel not in VALID_CHANNELS:
        raise ValueError(f"Invalid channel '{channel}'. Must be one of: {', '.join(sorted(VALID_CHANNELS))}")

    if not data.get("name", "").strip():
        raise ValueError("Template 'name' is required.")

    store = _load()
    existing_id = data.get("id", "").strip()
    is_default = bool(data.get("is_default", False))

    # Enforce uniqueness per channel if this one is default
    if is_default:
        for tpl in store.values():
            if tpl.get("channel") == channel and tpl.get("id") != existing_id:
                tpl["is_default"] = False

    if existing_id and existing_id in store:
        # ── Update existing ──────────────────────────────────────────────────
        existing = store[existing_id]
        _push_version(existing)                          # snapshot before overwrite

        existing["name"]        = data.get("name",        existing["name"])
        existing["channel"]     = channel
        existing["description"] = data.get("description", existing.get("description", ""))
        existing["subject"]     = data.get("subject",     existing.get("subject", ""))
        existing["body_html"]   = data.get("body_html",   existing.get("body_html", ""))
        existing["body_text"]   = data.get("body_text",   existing.get("body_text", ""))
        existing["header"]      = data.get("header",      existing.get("header", ""))
        existing["footer"]      = data.get("footer",      existing.get("footer", ""))
        existing["tags"]        = data.get("tags",        existing.get("tags", []))
        existing["is_default"]  = is_default
        existing["updated_at"]  = _now_iso()

        # Re-derive variable list from current body fields
        all_text = " ".join([
            existing.get("subject", ""),
            existing.get("body_html", ""),
            existing.get("body_text", ""),
        ])
        existing["variables"] = _extract_variables(all_text)

        _save(store)
        logger.info(f"[TEMPLATES] Updated template '{existing_id}' (v{len(existing.get('versions', []))})")
        return {k: v for k, v in existing.items() if k != "versions"}

    else:
        # ── Create new ───────────────────────────────────────────────────────
        new_id = str(uuid.uuid4())
        now    = _now_iso()

        all_text = " ".join([
            data.get("subject", ""),
            data.get("body_html", ""),
            data.get("body_text", ""),
        ])

        template: dict = {
            "id":          new_id,
            "name":        data["name"].strip(),
            "channel":     channel,
            "description": data.get("description", ""),
            "subject":     data.get("subject", ""),
            "body_html":   data.get("body_html", ""),
            "body_text":   data.get("body_text", ""),
            "header":      data.get("header", ""),
            "footer":      data.get("footer", ""),
            "tags":        data.get("tags", []),
            "is_default":  is_default,
            "variables":   _extract_variables(all_text),
            "created_at":  now,
            "updated_at":  now,
            "versions":    [],
        }
        store[new_id] = template
        _save(store)
        logger.info(f"[TEMPLATES] Created template '{new_id}' ({channel})")
        return {k: v for k, v in template.items() if k != "versions"}


def import_templates(templates: list[dict], mode: str = "restore") -> int:
    """
    Import a list of templates.
    mode="restore": Keeps the original UUID. Overwrites existing templates with the same UUID.
                    Ideal for automated backups.
    mode="duplicate": Generates new UUIDs and appends " (Imported)" to the name.
                      Ideal for sharing templates manually without risking overwrites.
    
    :param templates: List of template dictionaries.
    :param mode: 'restore' or 'duplicate'
    :returns: Number of templates successfully imported.
    """
    if not templates:
        return 0

    count = 0
    for data in templates:
        tpl_data = deepcopy(data)
        
        if mode == "duplicate":
            # Remove ID to force creation of a new UUID
            tpl_data.pop("id", None)
            
            # Append suffix if not already present
            name = tpl_data.get("name", "Imported Template").strip()
            if not name.endswith("(Imported)"):
                tpl_data["name"] = f"{name} (Imported)"
                
            # Prevent changing the default template unintentionally
            tpl_data["is_default"] = False
            
        try:
            save_template(tpl_data)
            count += 1
        except Exception as e:
            logger.error(f"[TEMPLATES] Failed to import template '{tpl_data.get('name', 'Unknown')}': {e}")
            
    return count


def delete_template(template_id: str) -> bool:
    """
    Permanently delete a template.

    :param template_id: The template UUID string.
    :returns: True if deleted, False if not found.
    """
    store = _load()
    if template_id not in store:
        return False
    name = store[template_id].get("name", template_id)
    del store[template_id]
    _save(store)
    logger.info(f"[TEMPLATES] Deleted template '{template_id}' ({name})")
    return True


def render_template(template_id: str, variables: dict) -> dict:
    """
    Interpolate variables into a template and return the ready-to-send content.

    :param template_id: The template UUID string.
    :param variables:   Dict of variable values, e.g. {"nome": "Mario", "prodotto": "Hecos"}.
    :returns: Dict with keys: subject, body_html, body_text.
    :raises KeyError: If template_id is not found.
    """
    tpl = get_template(template_id)
    if tpl is None:
        raise KeyError(f"Template '{template_id}' not found.")

    return {
        "subject":   _interpolate(tpl.get("subject",   ""), variables),
        "body_html": _interpolate(tpl.get("body_html", ""), variables),
        "body_text": _interpolate(tpl.get("body_text", ""), variables),
        # Header and footer are static: NOT interpolated — intentional feature
        "header":    tpl.get("header", ""),
        "footer":    tpl.get("footer", ""),
    }


def get_version_history(template_id: str) -> list[dict]:
    """
    Return the version history (snapshots) of a template, most-recent first.

    :param template_id: The template UUID string.
    :returns: List of version snapshot dicts.
    :raises KeyError: If template_id is not found.
    """
    tpl = get_template(template_id)
    if tpl is None:
        raise KeyError(f"Template '{template_id}' not found.")
    history = tpl.get("versions", [])
    return list(reversed(history))  # most recent first


def restore_version(template_id: str, version_index: int) -> dict:
    """
    Restore a template to a specific version (by position in history, 0 = most recent).

    The current state is pushed to history before restoring, so nothing is lost.

    :param template_id:    The template UUID string.
    :param version_index:  0-based index into get_version_history() result.
    :returns: The newly restored template dict (without version history).
    :raises KeyError:   If template_id is not found.
    :raises IndexError: If version_index is out of range.
    """
    store = _load()
    if template_id not in store:
        raise KeyError(f"Template '{template_id}' not found.")

    existing = store[template_id]
    history  = list(reversed(existing.get("versions", [])))  # most recent first

    if version_index < 0 or version_index >= len(history):
        raise IndexError(f"Version index {version_index} out of range (0–{len(history)-1}).")

    target_snapshot = history[version_index]

    # Push current state before overwriting
    _push_version(existing)

    # Restore snapshot fields
    for field in ("name", "channel", "description", "subject",
                  "body_html", "body_text", "header", "footer", "tags", "is_default", "variables"):
        if field in target_snapshot:
            existing[field] = target_snapshot[field]

    existing["updated_at"] = _now_iso()
    _save(store)

    logger.info(f"[TEMPLATES] Restored template '{template_id}' to version #{version_index}")
    return {k: v for k, v in existing.items() if k != "versions"}
