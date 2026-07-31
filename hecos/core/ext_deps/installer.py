"""
installer.py
─────────────────────────────────────────────────────────────────────────────
Hecos External Dependency Manager — Silent Installer
─────────────────────────────────────────────────────────────────────────────
Executes external installers silently and tracks installed state in a
JSON file under the user's home directory.

Cross-platform: uses pathlib and os.path.expanduser for all paths.
The installed-deps tracking file is stored at:
  ~/.hecos/installed_ext_deps.json
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

from hecos.core.logging import logger
from .registry import ExternalDep
from .checker import invalidate_cache

# Tracking file: ~/.hecos/installed_ext_deps.json
# Works on Windows (%USERPROFILE%\.hecos\), Linux/macOS (~/.hecos/)
_HECOS_USER_DIR = Path.home() / ".hecos"
_INSTALLED_DB   = _HECOS_USER_DIR / "installed_ext_deps.json"

# Installer exit codes that indicate success
_SUCCESS_CODES = {
    0,     # OK
    3010,  # Windows: success, reboot required
    1641,  # Windows: success, reboot initiated
}


# ── Tracking helpers ───────────────────────────────────────────────────────────

def _load_db() -> dict:
    if _INSTALLED_DB.exists():
        try:
            return json.loads(_INSTALLED_DB.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_db(db: dict) -> None:
    _HECOS_USER_DIR.mkdir(parents=True, exist_ok=True)
    _INSTALLED_DB.write_text(
        json.dumps(db, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def is_tracked_installed(dep_id: str) -> bool:
    """True if this dep was previously installed and tracked by EDM."""
    return _load_db().get(dep_id, {}).get("installed", False)


def _mark_installed(dep_id: str, version: str = "") -> None:
    db = _load_db()
    import datetime
    db[dep_id] = {
        "installed": True,
        "version": version,
        "installed_at": datetime.datetime.now().isoformat(),
    }
    _save_db(db)


# ── Main installer ─────────────────────────────────────────────────────────────

def install(dep: ExternalDep, installer_path: Path) -> tuple[bool, str]:
    """
    Runs the installer silently.

    Returns:
        (success: bool, message: str)

    On non-relevant platforms (e.g. vc_redist on Linux), returns (True, "N/A").
    """
    if not dep.is_platform_relevant:
        return True, f"Dependency '{dep.name}' is not required on this platform."

    if not installer_path.exists():
        logger.error("EDM", f"Installer file not found: {installer_path}")
        return False, f"Installer file not found: {installer_path}"

    filename = installer_path.name.lower()

    # Build command based on file type and platform
    if sys.platform == "win32":
        if filename.endswith(".msi"):
            cmd = ["msiexec.exe", "/i", str(installer_path)] + dep.install_args
        else:
            cmd = [str(installer_path)] + dep.install_args
    else:
        # On Linux/macOS, .exe/.msi installers don't run natively.
        # This shouldn't happen (check platforms in catalog), but guard gracefully.
        logger.error("EDM", f"Cannot install '{dep.name}' on {sys.platform}: installer is a Windows executable.")
        return False, (
            f"Cannot install '{dep.name}' on {sys.platform}: "
            "installer is a Windows executable. Please install manually."
        )

    try:
        logger.info("EDM", f"Executing silent installer for '{dep.name}': {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5-minute timeout for heavy installers
        )

        if result.returncode in _SUCCESS_CODES:
            _mark_installed(dep.id, dep.version)
            invalidate_cache(dep.id)  # force re-check next time
            msg = (
                f"'{dep.name}' installed successfully."
                if result.returncode == 0
                else f"'{dep.name}' installed — a system restart may be required."
            )
            logger.info("EDM", f"Install succeeded for '{dep.name}' with exit code {result.returncode}")
            return True, msg
        else:
            stderr = result.stderr.strip() or f"Exit code {result.returncode}"
            logger.error("EDM", f"Install failed for '{dep.name}': {stderr}")
            return False, f"Installation failed for '{dep.name}': {stderr}"

    except subprocess.TimeoutExpired:
        logger.error("EDM", f"Installation of '{dep.name}' timed out after 5 minutes.")
        return False, f"Installation of '{dep.name}' timed out after 5 minutes."
    except FileNotFoundError:
        logger.error("EDM", f"Could not run installer: {installer_path}")
        return False, f"Could not run installer: {installer_path}"
    except Exception as e:
        logger.error("EDM", f"Unexpected error installing '{dep.name}': {e}")
        return False, f"Unexpected error installing '{dep.name}': {e}"
