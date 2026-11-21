import os
import re
from typing import List, Optional, Tuple

try:
    import tomllib  # Python 3.11+
except ImportError:  # pragma: no cover
    tomllib = None  # type: ignore[assignment]

from .install_registry import (
    default_tray_dir,
    find_tray_dir,
    read_registry,
    update_registry,
    validate_install_path,
)

# Paths and Constants
CWD = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PIPER_DIR = os.path.join(CWD, "bin", "piper")
PIPER_REPO_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0"
SYSTEM_CONFIG_PATH = os.path.join(CWD, "hecos", "config", "data", "system.yaml")
AUDIO_CONFIG_PATH = os.path.join(CWD, "hecos", "config", "data", "audio.yaml")
LOGO_PATH = os.path.join(CWD, "hecos", "assets", "Hecos_Logo_SQR_NBG_LogoOnly.png")


def _find_tray_dir(override: Optional[str] = None) -> Tuple[Optional[str], bool]:
    """Locate the Hecos-Tray directory via the shared install contract."""
    return find_tray_dir(CWD, override=override)


TRAY_DIR, TRAY_DIR_VERSIONED = _find_tray_dir()
TRAY_DIR_CANONICAL = default_tray_dir(CWD)


def refresh_tray_dir(override: Optional[str] = None) -> Tuple[Optional[str], bool]:
    """Refresh module-level TRAY_DIR globals (e.g. after --tray-dir or install)."""
    global TRAY_DIR, TRAY_DIR_VERSIONED
    TRAY_DIR, TRAY_DIR_VERSIONED = _find_tray_dir(override=override)
    return TRAY_DIR, TRAY_DIR_VERSIONED


VOICE_MAP = {
    "en": {"female": "en_US-lessac-low", "male": "en_US-bryce-medium"},
    "it": {"female": "it_IT-paola-medium", "male": "it_IT-riccardo-x_low"},
}


def parse_pyproject_dependencies(
    toml_path: str,
    extras: Tuple[str, ...] = ("service",),
    strip_specifiers: bool = False,
) -> List[str]:
    """Parse project dependencies (and optional extras) from pyproject.toml.

    Uses Python's stdlib ``tomllib`` so bracketed extras like ``misaki[en]``
    and environment markers like ``pywin32; sys_platform=='win32'`` are never
    truncated or lost.
    """
    if not os.path.isfile(toml_path):
        return []

    raw_packages: List[str] = []
    if tomllib is not None:
        try:
            with open(toml_path, "rb") as f:
                data = tomllib.load(f)
            project = data.get("project", {})
            raw_packages.extend(project.get("dependencies", []) or [])
            opt = project.get("optional-dependencies", {}) or {}
            for extra in extras:
                raw_packages.extend(opt.get(extra, []) or [])
        except Exception:
            raw_packages = []

    # Fallback parser if tomllib is unavailable (Python 3.10) or failed:
    # parse line-by-line within [project] sections rather than non-greedy regex
    # so brackets inside quoted strings (e.g. "misaki[en]") never cut off the list.
    if not raw_packages:
        try:
            with open(toml_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            target_keys = {"dependencies"} | set(extras)
            in_array = False
            for line in lines:
                stripped = line.strip()
                if not in_array:
                    for key in target_keys:
                        if re.match(rf"^{re.escape(key)}\s*=\s*\[", stripped):
                            in_array = True
                            # Handle single-line array
                            if stripped.endswith("]"):
                                raw_packages.extend(re.findall(r'"([^"]+)"', stripped))
                                in_array = False
                            break
                else:
                    if stripped.startswith("]"):
                        in_array = False
                        continue
                    if stripped.startswith("#"):
                        continue
                    raw_packages.extend(re.findall(r'"([^"]+)"', stripped))
        except Exception:
            return []

    if not strip_specifiers:
        # Deduplicate preserving order
        seen = set()
        result: List[str] = []
        for pkg in raw_packages:
            cleaned = pkg.strip()
            if cleaned and cleaned not in seen:
                seen.add(cleaned)
                result.append(cleaned)
        return result

    # Strip extras, version constraints and markers for uninstall/inspection
    names: List[str] = []
    seen_names = set()
    for pkg in raw_packages:
        name = re.split(r"[\[\];>=<~!@]", pkg)[0].strip()
        if name and name.lower() not in seen_names:
            seen_names.add(name.lower())
            names.append(name)
    return names


def safe_replace_yaml(filepath: str, key: str, value: str) -> bool:
    if not os.path.exists(filepath):
        return False

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    safe_value = str(value).replace("\\", "\\\\")
    # Match key at start of line OR with spaces (handles nested yaml)
    pattern = rf"(?m)^(\s*){key}:\s*.*$"
    replacement = rf"\1{key}: {safe_value}"

    new_content = re.sub(pattern, replacement, content)

    if new_content != content:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)
        return True

    # If content already matches, check if the key is present
    if re.search(pattern, content):
        return True  # Considered successful if already set to target

    return False


def get_current_system_lang() -> str:
    if os.path.exists(SYSTEM_CONFIG_PATH):
        with open(SYSTEM_CONFIG_PATH, "r", encoding="utf-8") as f:
            m = re.search(r"language:\s*(.*)", f.read())
            if m:
                return m.group(1).strip().lower()
    return "en"


__all__ = [
    "CWD",
    "PIPER_DIR",
    "PIPER_REPO_URL",
    "SYSTEM_CONFIG_PATH",
    "AUDIO_CONFIG_PATH",
    "LOGO_PATH",
    "TRAY_DIR",
    "TRAY_DIR_VERSIONED",
    "TRAY_DIR_CANONICAL",
    "VOICE_MAP",
    "refresh_tray_dir",
    "parse_pyproject_dependencies",
    "safe_replace_yaml",
    "get_current_system_lang",
    "read_registry",
    "update_registry",
    "validate_install_path",
]
