"""
MODULE: core/keys/key_loader.py
DESCRIPTION: Loads API keys from multiple sources (keys.yaml, .env, system.yaml).
             Priority order: keys_yaml > env > system_yaml (fallback).
             Deduplication: same (provider, value) pair is loaded only once.

.env EXTENDED FORMAT
====================
Standard (single key, backward-compatible):
    GROQ_API_KEY=gsk_xxx

Multi-key with optional inline description (comment after #):
    GROQ_API_KEY_1=gsk_principale     # Groq - account personale
    GROQ_API_KEY_2=gsk_backup         # Groq - account team
    GROQ_API_KEY_3=gsk_emergency      # Groq - account emergenza
    GEMINI_API_KEY_1=AIzaSy...        # Google AI Studio - progetto Zentra
    GEMINI_API_KEY_2=AIzaSy...        # Google AI Studio - backup

Both forms can coexist. Indexed keys take precedence over the bare key in ordering.
"""

import os
import re
from pathlib import Path
from typing import List, Tuple, Optional

from zentra.core.keys.key_store import ApiKeyEntry, STATUS_UNKNOWN

# Try to import YAML loader (used by Zentra config)
try:
    import yaml
    _YAML_AVAILABLE = True
except ImportError:
    _YAML_AVAILABLE = False

# Root project directory: the 'zentra/' black-box folder
# key_loader.py is at: zentra/core/keys/key_loader.py
# .parent        → zentra/core/keys/
# .parent.parent → zentra/core/
# .parent.parent.parent → zentra/   ← BLACK BOX ROOT
_PROJECT_ROOT = Path(__file__).parent.parent.parent
_KEYS_YAML_PATH = _PROJECT_ROOT / "config" / "keys.yaml"
_ENV_PATH = _PROJECT_ROOT / ".env"

# Canonical env var base names per provider
_ENV_KEY_MAP = {
    "groq":         "GROQ_API_KEY",
    "openai":       "OPENAI_API_KEY",
    "anthropic":    "ANTHROPIC_API_KEY",
    "gemini":       "GEMINI_API_KEY",
    "mistral":      "MISTRAL_API_KEY",
    "cohere":       "COHERE_API_KEY",
    "perplexity":   "PERPLEXITY_API_KEY",
    "stability":    "STABILITY_API_KEY",
    "pollinations": "POLLINATIONS_API_KEY",
    "huggingface":  "HUGGINGFACE_API_KEY",
}

# Reverse map: base env var name → provider
_ENV_REVERSE_MAP = {v: k for k, v in _ENV_KEY_MAP.items()}

# Regex to detect indexed env vars: GROQ_API_KEY_1, GROQ_API_KEY_12, etc.
_INDEXED_SUFFIX = re.compile(r"^(.+?)_(\d+)$")


def _parse_dotenv_extended(path: Path) -> List[Tuple[str, str, str]]:
    """
    Extended .env parser.
    Returns list of (env_var_name, value, description) tuples.

    Handles:
      KEY=value                    → (KEY, value, "")
      KEY=value  # description     → (KEY, value, "description")
      KEY="value" # description    → (KEY, value, "description")
    Ignores comment-only lines and blank lines.
    """
    result = []
    if not path.exists():
        return result

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            raw = line.rstrip("\n")
            stripped = raw.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if "=" not in stripped:
                continue

            key, _, rest = stripped.partition("=")
            key = key.strip()

            # Split value from inline comment
            # Format: value # description  (but only outside quotes)
            description = ""
            value = rest

            # Remove surrounding quotes first, then look for #
            unquoted = rest.strip()
            if unquoted.startswith('"') or unquoted.startswith("'"):
                q = unquoted[0]
                end_q = unquoted.find(q, 1)
                if end_q > 0:
                    value = unquoted[1:end_q]
                    after = unquoted[end_q + 1:].strip()
                    if after.startswith("#"):
                        description = after[1:].strip()
            else:
                # No quotes — split on first #
                # No quotes — split on first # (look for space-hash first for better precision, then any hash)
                if " #" in unquoted:
                    val_part, _, desc_part = unquoted.partition(" #")
                    value = val_part.strip()
                    description = desc_part.strip()
                elif "#" in unquoted:
                    val_part, _, desc_part = unquoted.partition("#")
                    value = val_part.strip()
                    description = desc_part.strip()
                elif "\t#" in unquoted:
                    val_part, _, desc_part = unquoted.partition("\t#")
                    value = val_part.strip()
                    description = desc_part.strip()
                else:
                    value = unquoted.strip()

            value = value.strip().strip('"').strip("'")
            if value:
                result.append((key, value, description))

    return result


def _resolve_provider_from_env_var(env_var: str) -> Optional[str]:
    """
    Given an env var name (with or without index suffix), return the provider name.
    Examples:
        GROQ_API_KEY       → groq
        GROQ_API_KEY_1     → groq
        GEMINI_API_KEY_3   → gemini
        MY_CUSTOM_KEY      → None (unknown)
    """
    # Try direct match first
    if env_var in _ENV_REVERSE_MAP:
        return _ENV_REVERSE_MAP[env_var]

    # Try stripping numeric suffix
    m = _INDEXED_SUFFIX.match(env_var)
    if m:
        base = m.group(1)
        if base in _ENV_REVERSE_MAP:
            return _ENV_REVERSE_MAP[base]

    return None


def load_keys() -> List[ApiKeyEntry]:
    """
    Load all API keys from all sources and return a deduplicated list of ApiKeyEntry.
    Order: keys.yaml (highest priority) → .env (extended, multi-key) → system.yaml (fallback).
    """
    entries: List[ApiKeyEntry] = []
    seen: set = set()  # (provider, value) tuples for deduplication

    def _add(provider: str, value: str, description: str, source: str):
        value = value.strip().strip('"').strip("'")
        if not value:
            return
        key = (provider.lower(), value)
        if key in seen:
            return
        seen.add(key)
        entries.append(ApiKeyEntry(
            provider=provider.lower(),
            value=value,
            description=description,
            source=source,
            status=STATUS_UNKNOWN,
        ))

    # ─── SOURCE 1: config/keys.yaml ─────────────────────────────────────────
    if _YAML_AVAILABLE and _KEYS_YAML_PATH.exists():
        try:
            with open(_KEYS_YAML_PATH, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            for provider, entries_list in data.items():
                if not isinstance(entries_list, list):
                    continue
                for item in entries_list:
                    if isinstance(item, dict):
                        val = item.get("value", "")
                        desc = item.get("description", "")
                    else:
                        val = str(item)
                        desc = ""
                    _add(provider, val, desc, "keys_yaml")
        except Exception as e:
            print(f"[KeyLoader] Warning: could not load keys.yaml: {e}")

    # ─── SOURCE 2: .env file (extended multi-key format) ────────────────────
    dotenv_rows = _parse_dotenv_extended(_ENV_PATH)

    # Build indexed map: {base_var: [(index_or_0, value, description)]}
    # Separates bare KEY= from indexed KEY_1=, KEY_2=, etc.
    bare_keys: dict = {}    # base_var → (value, description)
    indexed_keys: dict = {} # base_var → sorted list of (index, value, description)

    for env_var, val, desc in dotenv_rows:
        m = _INDEXED_SUFFIX.match(env_var)
        if m:
            base = m.group(1)
            idx = int(m.group(2))
            indexed_keys.setdefault(base, []).append((idx, val, desc))
        else:
            bare_keys[env_var] = (val, desc)

    # Load indexed keys first (sorted by index), then bare keys as fallback
    all_base_vars = set(list(indexed_keys.keys()) + list(bare_keys.keys()))

    for base_var in all_base_vars:
        provider = _resolve_provider_from_env_var(base_var)
        if not provider:
            continue  # Unknown provider, skip

        # Indexed first (KEY_1, KEY_2, ...)
        if base_var in indexed_keys:
            for _idx, val, desc in sorted(indexed_keys[base_var], key=lambda x: x[0]):
                label = desc if desc else f"From .env ({base_var}_{_idx})"
                _add(provider, val, label, "env")

        # Bare key as additional entry (if not already seen)
        if base_var in bare_keys:
            val, desc = bare_keys[base_var]
            label = desc if desc else f"From .env ({base_var})"
            _add(provider, val, label, "env")

    # Also check OS environment (for keys set outside .env, e.g. CI/CD)
    for provider, base_var in _ENV_KEY_MAP.items():
        val = os.environ.get(base_var, "").strip().strip('"').strip("'")
        if val:
            _add(provider, val, f"OS env ({base_var})", "env_os")

    # ─── SOURCE 3: system.yaml llm.providers fallback ───────────────────────
    _load_from_system_yaml(entries, seen, _add)

    return entries


def _load_from_system_yaml(entries, seen, add_fn):
    """Load api_key fields from config/system.yaml as last-resort fallback."""
    system_yaml = _PROJECT_ROOT / "config" / "system.yaml"
    if not _YAML_AVAILABLE or not system_yaml.exists():
        return
    try:
        with open(system_yaml, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        providers = data.get("llm", {}).get("providers", {})
        for provider, pcfg in providers.items():
            if isinstance(pcfg, dict):
                val = pcfg.get("api_key", "")
                if val:
                    add_fn(provider, val, "Legacy — from system.yaml", "system_yaml")
    except Exception as e:
        print(f"[KeyLoader] Warning: could not load system.yaml for keys: {e}")


# ─── Persistence helpers (keys.yaml) ────────────────────────────────────────

def save_key(provider: str, value: str, description: str = "") -> bool:
    """
    Append a new key entry to config/keys.yaml. Returns True on success.
    Keys added via WebUI always go to keys.yaml (not .env).
    """
    if not _YAML_AVAILABLE:
        return False
    try:
        data = {}
        if _KEYS_YAML_PATH.exists():
            with open(_KEYS_YAML_PATH, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

        provider = provider.lower()
        if provider not in data:
            data[provider] = []

        # Avoid duplicates in file
        for existing in data[provider]:
            if isinstance(existing, dict) and existing.get("value") == value:
                return False  # Already exists

        data[provider].append({"value": value, "description": description})

        with open(_KEYS_YAML_PATH, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        return True
    except Exception as e:
        print(f"[KeyLoader] Error saving key: {e}")
        return False


def save_key_to_env(provider: str, value: str, description: str = "") -> bool:
    """
    Append a new indexed key entry to .env, grouping it with existing keys.
    Finds the next available index for the provider and inserts:
        PROVIDER_API_KEY_N=value  # description
    right below the last matching key of the same provider.
    Returns True on success.
    """
    base_var = _ENV_KEY_MAP.get(provider.lower())
    if not base_var:
        # For unknown providers, create a canonical name
        base_var = f"{provider.upper()}_API_KEY"

    # 1) Parse file to find max_idx and last matching line index
    if not _ENV_PATH.exists():
        lines = []
    else:
        with open(_ENV_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()

    max_idx = 0
    last_match_line_idx = -1

    for i, line in enumerate(lines):
        raw = line.split("#")[0].strip()
        if "=" in raw:
            k, _, _ = raw.partition("=")
            k = k.strip()
            if k == base_var:
                last_match_line_idx = i
            else:
                m = _INDEXED_SUFFIX.match(k)
                if m and m.group(1) == base_var:
                    last_match_line_idx = i
                    max_idx = max(max_idx, int(m.group(2)))

    # 2) Prepare the new line
    next_idx = max_idx + 1
    new_var = f"{base_var}_{next_idx}"
    desc_part = f"  # {description}" if description else ""
    new_line = f"{new_var}={value}{desc_part}\n"

    # 3) Insert and save
    try:
        if last_match_line_idx == -1:
            # Provide doesn't exist yet, append to bottom
            if lines and not lines[-1].endswith("\n"):
                lines[-1] += "\n"
            lines.append(f"\n{new_line}")
        else:
            # Insert right after the last occurrence
            lines.insert(last_match_line_idx + 1, new_line)

        logger.info(f"[KeyLoader] Writing {len(lines)} lines to {_ENV_PATH}")
        with open(_ENV_PATH, "w", encoding="utf-8") as f:
            f.writelines(lines)
        return True
    except Exception as e:
        logger.error(f"[KeyLoader] Failed to write .env: {e}")
        return False


def remove_key(provider: str, value: str) -> bool:
    """
    Remove a key from config/keys.yaml. Returns True on success.
    Note: .env keys are not auto-removed (the user owns that file).
    """
    if not _YAML_AVAILABLE or not _KEYS_YAML_PATH.exists():
        return False
    try:
        with open(_KEYS_YAML_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        provider = provider.lower()
        if provider not in data:
            return False

        before = len(data[provider])
        data[provider] = [
            e for e in data[provider]
            if not (isinstance(e, dict) and e.get("value") == value)
        ]
        if len(data[provider]) == before:
            return False  # Nothing removed

        with open(_KEYS_YAML_PATH, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        return True
    except Exception as e:
        print(f"[KeyLoader] Error removing key: {e}")
        return False
