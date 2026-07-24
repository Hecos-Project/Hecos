"""
__init__.py
─────────────────────────────────────────────────────────────────────────────
Hecos External Dependency Manager (EDM) — Public API
─────────────────────────────────────────────────────────────────────────────

Usage from any Hecos component:

    from hecos.core.ext_deps import require, is_installed

    # Lazy check — blocks feature gracefully if dep is missing
    if not require("tesseract"):
        return "⚠️ Tesseract OCR not installed. Visit /settings/deps to install."

    # Non-blocking check (no notification)
    if not is_installed("vc_redist"):
        logger.warning("VC Redist missing — Piper TTS may not work.")

    # Trigger install from code (e.g. from a WebUI API endpoint)
    from hecos.core.ext_deps import install_dep
    success, msg = install_dep("tesseract")
"""
from __future__ import annotations

import threading
from pathlib import Path
from typing import Optional

from .registry import ExternalDep, get_dep, get_all_deps
from .checker import is_installed as _is_installed
from .downloader import download
from .installer import install, is_tracked_installed
from .notifier import (
    notify_missing,
    notify_downloading,
    notify_installing,
    notify_done,
    notify_skipped,
)

# The local fallback directory (retrocompatibility with old dependencies/ folder)
_LOCAL_FALLBACK = Path(__file__).parents[3] / "dependencies"


def is_installed(dep_id: str) -> bool:
    """
    Returns True if the dependency is present on this system.
    No side effects — does not notify or install anything.
    """
    dep = get_dep(dep_id)
    if dep is None:
        return True  # unknown dep → don't block
    if is_tracked_installed(dep_id):
        return True  # fast path: we installed it ourselves
    return _is_installed(dep)


def require(dep_id: str) -> bool:
    """
    Lazy presence check with user notification.

    - Returns True immediately if the dep is already installed.
    - If missing: notifies the user (console + WebUI SSE banner) and returns False.
    - Does NOT auto-install — the user must trigger install via WebUI or CLI.

    This is the primary integration point for components:

        from hecos.core.ext_deps import require
        if not require("tesseract"):
            return "Feature unavailable: Tesseract OCR not installed."
    """
    dep = get_dep(dep_id)
    if dep is None:
        return True  # not in catalog → assume OK (don't block unknown deps)

    if not dep.is_platform_relevant:
        return True  # not needed on this OS

    if is_installed(dep_id):
        return True

    notify_missing(dep)
    return False


def install_dep(dep_id: str, on_progress=None) -> tuple[bool, str]:
    """
    Downloads and installs a dependency synchronously.

    Intended for use from:
      - WebUI API endpoint (called in a thread)
      - CLI setup wizard
      - Auto-install for non-optional deps on first run

    Args:
        dep_id:      The dep id from ext_deps.toml
        on_progress: Optional callback(bytes_done, total) for download progress

    Returns:
        (success: bool, message: str)
    """
    dep = get_dep(dep_id)
    if dep is None:
        return False, f"Unknown dependency id: '{dep_id}'"

    if not dep.is_platform_relevant:
        return True, f"'{dep.id}' is not required on this platform — skipped."

    if is_installed(dep_id):
        notify_skipped(dep)
        return True, f"'{dep.name}' is already installed."

    # ── Download ──────────────────────────────────────────────────────────────
    def _progress_cb(done: int, total: int) -> None:
        notify_downloading(dep, done, total)
        if on_progress:
            on_progress(done, total)

    try:
        installer_path = download(
            dep,
            progress_cb=_progress_cb,
            local_fallback_dir=_LOCAL_FALLBACK if _LOCAL_FALLBACK.exists() else None,
        )
    except (ConnectionError, ValueError, FileNotFoundError) as e:
        msg = str(e)
        notify_done(dep, success=False, message=msg)
        return False, msg

    # ── Install ───────────────────────────────────────────────────────────────
    notify_installing(dep)
    success, message = install(dep, installer_path)
    notify_done(dep, success=success, message=message)
    return success, message


def install_dep_async(dep_id: str, on_done=None) -> threading.Thread:
    """
    Runs install_dep() in a background thread.
    Useful for WebUI endpoints that must not block the request.

    Args:
        dep_id:  The dep id.
        on_done: Optional callback(success: bool, message: str) called on completion.
    """
    def _run():
        success, msg = install_dep(dep_id)
        if on_done:
            on_done(success, msg)

    t = threading.Thread(target=_run, daemon=True, name=f"edm-install-{dep_id}")
    t.start()
    return t


def check_all_required() -> list[str]:
    """
    Checks all non-optional, platform-relevant deps.
    Notifies for each missing one.
    Returns a list of missing dep ids.
    """
    missing = []
    for dep in get_all_deps():
        if dep.optional:
            continue
        if not dep.is_platform_relevant:
            continue
        if not is_installed(dep.id):
            notify_missing(dep)
            missing.append(dep.id)
    return missing


def get_status_all() -> list[dict]:
    """
    Returns a list of status dicts for all deps (for WebUI API).
    """
    result = []
    for dep in get_all_deps():
        installed = is_installed(dep.id) if dep.is_platform_relevant else None
        result.append({
            "id":           dep.id,
            "name":         dep.name,
            "description":  dep.description,
            "version":      dep.version,
            "optional":     dep.optional,
            "required_by":  dep.required_by,
            "platforms":    dep.platforms,
            "platform_relevant": dep.is_platform_relevant,
            "installed":    installed,
            "download_url": dep.download_url,
        })
    return result
