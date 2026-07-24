"""
checker.py
─────────────────────────────────────────────────────────────────────────────
Hecos External Dependency Manager — Presence Checker
─────────────────────────────────────────────────────────────────────────────
Verifies whether an external dependency is already installed on the system.
All checks are read-only and cross-platform safe.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import Optional

from .registry import ExternalDep

# In-memory cache: dep_id → bool
_check_cache: dict[str, bool] = {}


# ── Check implementations ──────────────────────────────────────────────────────

def _check_executable(name: str) -> bool:
    """True if `name` is found in the system PATH (cross-platform)."""
    return shutil.which(name) is not None


def _check_registry_key(key_path: str) -> bool:
    """
    True if the given Windows registry key exists.
    Always returns True on non-Windows platforms (dep not applicable there).
    """
    if sys.platform != "win32":
        return True  # not relevant on this platform → treat as satisfied

    try:
        import winreg
        # Parse HIVE\path
        parts = key_path.split("\\", 1)
        if len(parts) != 2:
            return False
        hive_str, sub_key = parts[0], parts[1]

        hive_map = {
            "HKEY_LOCAL_MACHINE": winreg.HKEY_LOCAL_MACHINE,
            "HKLM": winreg.HKEY_LOCAL_MACHINE,
            "HKEY_CURRENT_USER": winreg.HKEY_CURRENT_USER,
            "HKCU": winreg.HKEY_CURRENT_USER,
        }
        hive = hive_map.get(hive_str.upper())
        if hive is None:
            return False

        try:
            with winreg.OpenKey(hive, sub_key):
                return True
        except FileNotFoundError:
            return False
    except ImportError:
        return True  # winreg not available (shouldn't happen on win32)
    except Exception:
        return False


def _check_path(path_str: str) -> bool:
    """True if the given path exists on the filesystem (cross-platform)."""
    return Path(path_str).exists()


# ── Public API ─────────────────────────────────────────────────────────────────

def is_installed(dep: ExternalDep, use_cache: bool = True) -> bool:
    """
    Returns True if the dependency is already satisfied on this system.

    - If the dep is not relevant for the current platform, always returns True.
    - Results are cached in memory to avoid repeated system calls.

    Args:
        dep:        The ExternalDep to check.
        use_cache:  If False, forces a fresh check (e.g. after installation).
    """
    if not dep.is_platform_relevant:
        return True  # dep does not apply to this OS

    if use_cache and dep.id in _check_cache:
        return _check_cache[dep.id]

    check_type = dep.check_type
    check_value = dep.check_value

    if check_type == "executable":
        result = _check_executable(check_value)
    elif check_type == "registry_key":
        result = _check_registry_key(check_value)
    elif check_type == "path":
        result = _check_path(check_value)
    else:
        # Unknown check type — assume not installed to be safe
        result = False

    _check_cache[dep.id] = result
    return result


def invalidate_cache(dep_id: Optional[str] = None) -> None:
    """
    Clears the check cache so the next call to is_installed() does a fresh check.
    Pass dep_id to clear only one entry, or None to clear all.
    """
    if dep_id is None:
        _check_cache.clear()
    else:
        _check_cache.pop(dep_id, None)
