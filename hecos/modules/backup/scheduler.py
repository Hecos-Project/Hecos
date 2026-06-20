"""
MODULE: Backup Scheduler
DESCRIPTION: APScheduler BackgroundScheduler wrapper for the Global Backup Orchestrator.
             Pattern mirrors hecos.plugins.reminder.scheduler.
             Runs in a daemon thread — does NOT block Flask.
"""

import threading
from datetime import datetime, timezone
from hecos.core.logging import logger
from hecos.modules.backup import store as backup_store

# ── APScheduler import (graceful fallback) ────────────────────────────────────
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.jobstores.memory import MemoryJobStore
    APSCHEDULER_AVAILABLE = True
except ImportError:
    APSCHEDULER_AVAILABLE = False
    logger.debug("BACKUP", "APScheduler not installed — auto-backup scheduler disabled.")

# ── Singleton state ───────────────────────────────────────────────────────────
_scheduler: "BackgroundScheduler | None" = None
_app_ref = None
_lock = threading.Lock()
_JOB_ID = "hecos_backup_job"


# ── Internal callback ─────────────────────────────────────────────────────────

def _run_backup_job() -> None:
    """Called by APScheduler at trigger time. Runs full backup in background."""
    if _app_ref is None:
        logger.warning("BACKUP", "Scheduler fired but no app reference. Skipping.")
        return
    try:
        cfg = backup_store.load()
        dest = cfg.get("destination", "")
        modules_enabled = cfg.get("modules", {})
        logger.info("BACKUP", "⏰ Scheduled backup started.")
        from hecos.modules.backup.orchestrator import run_full_backup
        result = run_full_backup(_app_ref, dest, modules_enabled)
        ts = datetime.now(timezone.utc).isoformat()
        outcome = "ok" if result.get("ok") else "error"
        backup_store.update_last_run(outcome, ts)
        if result.get("ok"):
            logger.info("BACKUP", f"✅ Scheduled backup OK → {result.get('filename')}")
        else:
            logger.error(f"[BACKUP] Scheduled backup failed: {result.get('error')}")
    except Exception as e:
        logger.error(f"[BACKUP] _run_backup_job error: {e}")


# ── Public API ────────────────────────────────────────────────────────────────

def start(app) -> None:
    """
    Initialise and start the BackgroundScheduler.
    Loads config and schedules the backup job if enabled.
    Safe to call multiple times — subsequent calls are no-ops.
    """
    global _scheduler, _app_ref

    if not APSCHEDULER_AVAILABLE:
        logger.debug("BACKUP", "APScheduler unavailable — scheduler not started.")
        return

    _app_ref = app

    with _lock:
        if _scheduler is not None and _scheduler.running:
            return

        _scheduler = BackgroundScheduler(jobstores={"default": MemoryJobStore()})
        _scheduler.start()
        logger.info("BACKUP", "✅ Backup scheduler started.")

    cfg = backup_store.load()
    if cfg.get("enabled") and cfg.get("schedule_cron"):
        _schedule_job(cfg["schedule_cron"])


def stop() -> None:
    """Gracefully shut down the scheduler."""
    global _scheduler
    with _lock:
        if _scheduler and _scheduler.running:
            try:
                _scheduler.shutdown(wait=False)
                logger.info("BACKUP", "Backup scheduler stopped.")
            except Exception as e:
                logger.debug("BACKUP", f"Scheduler stop error: {e}")
            _scheduler = None


def reschedule(cron_expr: str | None) -> bool:
    """
    Update the backup job cron expression live.
    Pass None or empty string to disable (remove) the job.
    """
    if not APSCHEDULER_AVAILABLE or _scheduler is None:
        return False
    try:
        # Remove existing job first
        if _scheduler.get_job(_JOB_ID):
            _scheduler.remove_job(_JOB_ID)
        if cron_expr:
            _schedule_job(cron_expr)
        return True
    except Exception as e:
        logger.error(f"[BACKUP] reschedule error: {e}")
        return False


def _schedule_job(cron_expr: str) -> None:
    """Internal: add the backup job with a CronTrigger."""
    try:
        parts = cron_expr.strip().split()
        if len(parts) == 5:
            trigger = CronTrigger(
                minute=parts[0], hour=parts[1], day=parts[2],
                month=parts[3], day_of_week=parts[4]
            )
        else:
            # Fallback for key=value format
            kwargs = dict(kv.split("=") for kv in parts if "=" in kv)
            trigger = CronTrigger(**kwargs)

        _scheduler.add_job(
            func=_run_backup_job,
            trigger=trigger,
            id=_JOB_ID,
            name="Hecos Global Backup",
            replace_existing=True,
            misfire_grace_time=600,
            coalesce=True,
        )
        logger.info("BACKUP", f"Backup job scheduled with cron: {cron_expr}")
    except Exception as e:
        logger.error(f"[BACKUP] _schedule_job error for cron '{cron_expr}': {e}")


def get_status() -> dict:
    """Return diagnostic info about the scheduler state."""
    if not APSCHEDULER_AVAILABLE or _scheduler is None:
        return {"running": False, "next_run": None}

    job = _scheduler.get_job(_JOB_ID) if _scheduler.running else None
    next_run = None
    if job and job.next_run_time:
        next_run = job.next_run_time.isoformat()

    cfg = backup_store.load()
    return {
        "running":      _scheduler.running,
        "enabled":      cfg.get("enabled", False),
        "next_run":     next_run,
        "last_backup":  cfg.get("last_backup"),
        "last_result":  cfg.get("last_result"),
        "cron":         cfg.get("schedule_cron"),
    }
