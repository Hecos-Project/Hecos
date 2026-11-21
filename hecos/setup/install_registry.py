"""
Hecos Setup - Shared Install Registry & Path Validation
Implements the shared contract between Hecos Core and Hecos Tray so both
can live in any valid directory on disk and reliably locate each other.

Registry file location:
  - Windows:     %LOCALAPPDATA%\\Hecos\\install.toml
  - Linux/macOS: ${XDG_CONFIG_HOME:-$HOME/.config}/hecos/install.toml
"""

from __future__ import annotations

import datetime
import glob
import os
import platform
import re
import tempfile
from typing import Dict, List, Optional, Tuple

try:
    import tomllib  # Python 3.11+
except ImportError:  # pragma: no cover - Python 3.10 fallback
    tomllib = None  # type: ignore[assignment]


FORBIDDEN_PATH_CHARS = set("!%^&()=;,`\"'")
RISKY_PATH_SEGMENTS = ("onedrive", "program files", "program files (x86)", "windows", "temp", "tmp")


def get_registry_path() -> str:
    """Return the canonical path to the shared Hecos install.toml registry."""
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.path.join(
            os.path.expanduser("~"), "AppData", "Local"
        )
        return os.path.join(base, "Hecos", "install.toml")
    xdg = os.environ.get("XDG_CONFIG_HOME") or os.path.join(
        os.path.expanduser("~"), ".config"
    )
    return os.path.join(xdg, "hecos", "install.toml")


def _fallback_parse_flat_toml(text: str) -> Dict[str, str]:
    """Minimal parser for flat key = 'value' or key = \"value\" TOML files."""
    data: Dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        key = k.strip()
        val = v.strip()
        if len(val) >= 2 and val[0] == "'" and val[-1] == "'":
            val = val[1:-1]
        elif len(val) >= 2 and val[0] == '"' and val[-1] == '"':
            val = val[1:-1].replace("\\\\", "\\").replace('\\"', '"')
        if key:
            data[key] = val
    return data


def read_registry(path: Optional[str] = None) -> Dict[str, str]:
    """Read the shared install.toml registry. Never raises on missing/corrupt files."""
    reg_path = path or get_registry_path()
    if not os.path.isfile(reg_path):
        return {}
    try:
        if tomllib is not None:
            with open(reg_path, "rb") as f:
                raw = tomllib.load(f)
            return {str(k): str(v) for k, v in raw.items() if v is not None}
        with open(reg_path, "r", encoding="utf-8", errors="replace") as f:
            return _fallback_parse_flat_toml(f.read())
    except Exception:
        try:
            with open(reg_path, "r", encoding="utf-8", errors="replace") as f:
                return _fallback_parse_flat_toml(f.read())
        except Exception:
            return {}


def _format_toml_value(value: str) -> str:
    """Format value as a TOML literal string (single-quoted) when possible.

    Literal strings contain no escape sequences, making them trivial to parse
    from Windows batch scripts as well as valid TOML 1.0.
    """
    cleaned = str(value).strip()
    if "'" not in cleaned and "\n" not in cleaned and "\r" not in cleaned:
        return f"'{cleaned}'"
    escaped = cleaned.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
    return f'"{escaped}"'


def update_registry(path: Optional[str] = None, **fields: Optional[str]) -> str:
    """Merge non-None keys into install.toml and write atomically.

    Preserves unrelated keys written by the sibling component (Core vs Tray).
    """
    reg_path = path or get_registry_path()
    data = read_registry(reg_path)

    for key, val in fields.items():
        if val is not None and str(val).strip() != "":
            data[key] = os.path.normpath(str(val)) if key.endswith(("_path", "_python")) else str(val)

    data["updated_at"] = datetime.datetime.now().replace(microsecond=0).isoformat()

    os.makedirs(os.path.dirname(reg_path), exist_ok=True)
    ordered_keys = ["core_path", "tray_path", "core_python", "tray_python", "updated_at"]
    extras = [k for k in sorted(data.keys()) if k not in ordered_keys]

    lines = [
        "# Hecos shared install registry (managed automatically by Core & Tray setup)",
    ]
    for key in ordered_keys + extras:
        if key in data and data[key] != "":
            lines.append(f"{key} = {_format_toml_value(data[key])}")

    content = "\n".join(lines) + "\n"

    # Atomic write via temp file in same directory
    reg_dir = os.path.dirname(reg_path)
    fd, tmp_path = tempfile.mkstemp(prefix=".install_", suffix=".tmp", dir=reg_dir)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        os.replace(tmp_path, reg_path)
    except Exception:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        with open(reg_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)

    return reg_path


def is_valid_core_dir(path: Optional[str]) -> bool:
    """Check whether path points to a real Hecos Core installation."""
    if not path:
        return False
    return os.path.isfile(os.path.join(path, "hecos", "core", "version"))


def is_valid_tray_dir(path: Optional[str]) -> bool:
    """Check whether path points to a real Hecos Tray installation."""
    if not path:
        return False
    return os.path.isfile(os.path.join(path, "tray", "version"))


def validate_install_path(path: str) -> Tuple[bool, List[str], List[str]]:
    """Validate an installation path according to the Hecos safety contract.

    Returns:
        (is_valid, errors, warnings)
        - errors: hard blockers (spaces, non-ASCII, shell metacharacters)
        - warnings: non-blocking advisories (OneDrive, Program Files, long paths)
    """
    errors: List[str] = []
    warnings: List[str] = []

    if not path or not path.strip():
        return False, ["Path is empty."], []

    norm = os.path.normpath(path.strip())

    # Check spaces
    if " " in norm:
        errors.append("Path contains spaces (breaks Python venvs and native build tools).")

    # Check non-ASCII
    if any(ord(ch) > 127 for ch in norm):
        errors.append("Path contains non-ASCII characters (can break pip/C++ tools).")

    # Check shell metacharacters (exclude drive colon on Windows like C:\)
    check_str = norm[2:] if (os.name == "nt" and len(norm) >= 2 and norm[1] == ":") else norm
    bad_chars = sorted({ch for ch in check_str if ch in FORBIDDEN_PATH_CHARS})
    if bad_chars:
        errors.append(f"Path contains unsafe characters: {' '.join(bad_chars)}")

    # Check Windows max path advisory
    if os.name == "nt" and len(norm) > 80:
        warnings.append(
            f"Path is {len(norm)} chars long (>80). Deep Python/Node paths may hit Windows limits."
        )

    # Check risky parent folders (OneDrive, Program Files, Windows, Temp)
    parts_lower = [p.lower() for p in re.split(r"[\\/]+", norm) if p]
    for seg in RISKY_PATH_SEGMENTS:
        if any(seg in part for part in parts_lower):
            if seg == "onedrive":
                warnings.append("Path is inside OneDrive (cloud sync can lock SQLite DBs and venv files).")
            elif "program files" in seg or seg == "windows":
                warnings.append("Path is inside a protected system folder (requires admin rights for updates).")
            elif seg in ("temp", "tmp"):
                warnings.append("Path is inside a temporary directory (OS cleanup may delete files).")
            break

    return (len(errors) == 0), errors, warnings


def default_core_dir() -> str:
    """Default suggested installation directory for Hecos Core."""
    if platform.system() == "Windows":
        return r"C:\Hecos"
    return os.path.join(os.path.expanduser("~"), "Hecos")


def default_tray_dir(core_root: Optional[str] = None) -> str:
    """Default canonical Tray directory (sibling of core_root if known)."""
    if core_root:
        parent = os.path.dirname(os.path.normpath(core_root))
        if parent and parent != os.path.normpath(core_root):
            return os.path.join(parent, "Hecos-Tray")
    if platform.system() == "Windows":
        return r"C:\Hecos-Tray"
    return os.path.join(os.path.expanduser("~"), "Hecos-Tray")


def find_tray_dir(
    core_root: str,
    override: Optional[str] = None,
) -> Tuple[Optional[str], bool]:
    """Locate Hecos-Tray following the shared resolution order.

    Order:
      1. Explicit override / env HECOS_TRAY_DIR
      2. Shared install.toml `tray_path`
      3. Sibling `<core_parent>/Hecos-Tray`
      4. Windows `<core_drive>:\\Hecos-Tray` & `C:\\Hecos-Tray` | POSIX `~/Hecos-Tray`, `/opt/hecos-tray`
      5. Versioned `Hecos-Tray-*` inside the same search parents

    Returns:
      (tray_path or None, is_versioned_folder)
    """
    norm_core = os.path.normpath(os.path.abspath(core_root))
    core_parent = os.path.dirname(norm_core)

    direct_candidates: List[str] = []
    if override:
        direct_candidates.append(override)
    env_tray = os.environ.get("HECOS_TRAY_DIR")
    if env_tray:
        direct_candidates.append(env_tray)

    reg = read_registry()
    if reg.get("tray_path"):
        direct_candidates.append(reg["tray_path"])

    # Sibling next to Core
    direct_candidates.append(os.path.join(core_parent, "Hecos-Tray"))

    search_parents: List[str] = [core_parent]
    if os.name == "nt":
        drive = os.path.splitdrive(norm_core)[0] or "C:"
        drive_root = drive + os.sep
        direct_candidates.append(os.path.join(drive_root, "Hecos-Tray"))
        search_parents.append(drive_root)
        if drive.upper() != "C:":
            direct_candidates.append(r"C:\Hecos-Tray")
            search_parents.append("C:\\")
    else:
        home = os.path.expanduser("~")
        direct_candidates.append(os.path.join(home, "Hecos-Tray"))
        direct_candidates.append("/opt/hecos-tray")
        search_parents.extend([home, "/opt"])

    seen = set()
    for cand in direct_candidates:
        if not cand:
            continue
        norm = os.path.normpath(os.path.abspath(cand))
        key = norm.lower() if os.name == "nt" else norm
        if key in seen:
            continue
        seen.add(key)
        if is_valid_tray_dir(norm):
            base = os.path.basename(norm).lower()
            is_versioned = base.startswith("hecos-tray-")
            return norm, is_versioned

    # Wildcard search for GitHub-extracted versioned folders (Hecos-Tray-1.5.4, etc.)
    seen_parents = set()
    for parent in search_parents:
        if not parent or not os.path.isdir(parent):
            continue
        pkey = parent.lower() if os.name == "nt" else parent
        if pkey in seen_parents:
            continue
        seen_parents.add(pkey)
        for cand in sorted(glob.glob(os.path.join(parent, "Hecos-Tray-*"))):
            if is_valid_tray_dir(cand):
                return os.path.normpath(cand), True

    return None, False
