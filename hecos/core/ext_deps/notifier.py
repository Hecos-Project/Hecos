"""
notifier.py
─────────────────────────────────────────────────────────────────────────────
Hecos External Dependency Manager — User Notifier
─────────────────────────────────────────────────────────────────────────────
Delivers notifications about missing/installing deps via:
  1. Console output (always works, even without WebUI)
  2. Hecos SSE bus (for WebUI banner/toast when WebUI is running)

The notifier never crashes if the SSE bus is unavailable.
"""
from __future__ import annotations

from typing import Optional
from hecos.core.logging import logger
from .registry import ExternalDep


# ── ANSI colors for console output (stripped on Windows if not supported) ──────
_RED    = "\033[91m"
_YELLOW = "\033[93m"
_GREEN  = "\033[92m"
_CYAN   = "\033[96m"
_RESET  = "\033[0m"
_BOLD   = "\033[1m"


def _console(msg: str) -> None:
    try:
        print(msg)
    except Exception:
        pass


def _emit_sse(event_type: str, payload: dict) -> None:
    """
    Pushes an event to the Hecos Core Event Bus and WebUI StateManager.
    Silently no-ops if WebUI/bus isn't running yet.
    """
    try:
        from hecos.core.events import bus
        bus.emit(f"ext_deps:{event_type}", payload)
    except Exception:
        pass
    try:
        from hecos.modules.web_ui.server import get_state_manager
        sm = get_state_manager()
        if sm is not None:
            sm.add_event(f"ext_deps:{event_type}", payload)
    except Exception:
        pass


_active_tasks: dict = {}

def _get_or_create_dep_task(dep: ExternalDep):
    try:
        from hecos.core.progress import progress
        task_id = f"edm:{dep.id}"
        if dep.id in _active_tasks:
            return _active_tasks[dep.id][1]
        phases = [("download", 65, "Download"), ("install", 35, "Installation")]
        ctx = progress.task(task_id, title=f"Dependency {dep.name}", source="EDM", phases=phases)
        t = ctx.__enter__()
        _active_tasks[dep.id] = (ctx, t)
        return t
    except Exception:
        return None


# ── Public notification functions ──────────────────────────────────────────────

def notify_missing(dep: ExternalDep) -> None:
    """
    Called when a dependency is not found.
    Logs to console and sends a WebUI banner event.
    """
    severity = "error" if not dep.optional else "warning"
    icon = "❌" if not dep.optional else "⚠️"

    _console(
        f"\n{_BOLD}{_RED if not dep.optional else _YELLOW}"
        f"{icon} [EDM] Missing external dependency: {dep.name} (v{dep.version}){_RESET}\n"
        f"   → Required by: {', '.join(dep.required_by)}\n"
        f"   → {dep.description}\n"
        f"   → Download: {dep.download_url or 'Not available for this platform'}\n"
    )
    logger.warning("EDM", f"Missing external dependency: {dep.name} (v{dep.version})")

    _emit_sse("missing", {
        "id":           dep.id,
        "name":         dep.name,
        "description":  dep.description,
        "version":      dep.version,
        "download_url": dep.download_url,
        "required_by":  dep.required_by,
        "optional":     dep.optional,
        "severity":     severity,
    })


def notify_downloading(dep: ExternalDep, bytes_done: int, total_bytes: int) -> None:
    """
    Called during download to report progress.
    Sends a progress event to the WebUI and updates the unified progress task.
    """
    pct = int(bytes_done / total_bytes * 100) if total_bytes > 0 else 0
    t = _get_or_create_dep_task(dep)
    if t:
        t.phase("download")
        t.advance(bytes_done=bytes_done, total_bytes=total_bytes, message=f"Downloading {dep.name}...")

    _emit_sse("download_progress", {
        "id":         dep.id,
        "name":       dep.name,
        "bytes_done": bytes_done,
        "total":      total_bytes,
        "percent":    pct,
    })


def notify_installing(dep: ExternalDep) -> None:
    """Called when the installer is being executed."""
    _console(f"{_CYAN}[EDM] Installing {dep.name}...{_RESET}")
    t = _get_or_create_dep_task(dep)
    if t:
        t.phase("install")
        t.advance(message=f"Installing {dep.name} in progress...", percent=50.0)
    _emit_sse("installing", {"id": dep.id, "name": dep.name})


def notify_done(dep: ExternalDep, success: bool, message: str = "") -> None:
    """Called when the installation attempt is complete."""
    if success:
        _console(f"{_GREEN}[EDM] ✓ {dep.name} installed successfully.{_RESET}\n")
        logger.info("EDM", f"{dep.name} installed successfully.")
    else:
        _console(
            f"{_RED}[EDM] ✗ Failed to install {dep.name}.\n"
            f"   → {message}\n"
            f"   → Please install manually: {dep.download_url}{_RESET}\n"
        )
        logger.error("EDM", f"Failed to install {dep.name}: {message}")

    if dep.id in _active_tasks:
        try:
            ctx, t = _active_tasks.pop(dep.id)
            if success:
                t.done(f"{dep.name} installed successfully.")
            else:
                t.fail(message or f"Installation of {dep.name} failed.")
            ctx.__exit__(None, None, None)
        except Exception:
            pass

    _emit_sse("install_done", {
        "id":      dep.id,
        "name":    dep.name,
        "success": success,
        "message": message,
    })


def notify_skipped(dep: ExternalDep, reason: str = "already installed") -> None:
    """Called when installation is skipped (dep already present)."""
    _emit_sse("skipped", {"id": dep.id, "name": dep.name, "reason": reason})
