"""
MODULE: Reminder Scheduler
DESCRIPTION: APScheduler BackgroundScheduler wrapper for the Reminder plugin.
             Manages all job lifecycle: add, cancel, reschedule (snooze), and
             bulk-reload from the DB on startup.

             The scheduler runs in its own daemon thread pool and does NOT
             block the main Hecos thread or the Flask request handlers.
"""

import threading
from datetime import datetime, timedelta
from hecos.core.logging import logger

# ── APScheduler import ────────────────────────────────────────────────────────
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.date import DateTrigger
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.jobstores.memory import MemoryJobStore
    APSCHEDULER_AVAILABLE = True
except ImportError:
    APSCHEDULER_AVAILABLE = False
    logger.debug("REMINDER", "APScheduler not installed — scheduler disabled.")


# ── Singleton state ───────────────────────────────────────────────────────────
_scheduler: "BackgroundScheduler | None" = None
_lock = threading.Lock()
_JOB_PREFIX = "reminder_"


# ── Internal helpers ──────────────────────────────────────────────────────────

def _job_id(reminder_id: str) -> str:
    return f"{_JOB_PREFIX}{reminder_id}"


def _fire_callback(reminder_id: str) -> None:
    """Called by APScheduler at trigger time. Delegates to notifier."""
    try:
        from hecos.plugins.reminder import store, notifier
        reminder = store.get_by_id(reminder_id)
        if reminder and reminder.get("status") == "active":
            notifier.fire_reminder(reminder)
    except Exception as e:
        logger.error(f"[REMINDER] Scheduler fire callback error: {e}")


# ── Public API ────────────────────────────────────────────────────────────────

def start() -> None:
    """
    Initialises and starts the BackgroundScheduler.
    Loads all 'active' reminders from the DB and schedules them.
    Safe to call multiple times — subsequent calls are no-ops if already running.
    """
    global _scheduler

    if not APSCHEDULER_AVAILABLE:
        logger.debug("REMINDER", "APScheduler unavailable — scheduler not started.")
        return

    with _lock:
        if _scheduler is not None and _scheduler.running:
            return  # already running

        jobstores  = {"default": MemoryJobStore()}
        _scheduler = BackgroundScheduler(jobstores=jobstores)
        _scheduler.start()
        logger.info("REMINDER", "✅ Scheduler started.")

    # Bulk-load persisted reminders
    _reload_from_db()


def stop() -> None:
    """Gracefully shuts down the scheduler."""
    global _scheduler
    with _lock:
        if _scheduler and _scheduler.running:
            try:
                _scheduler.shutdown(wait=False)
                logger.info("REMINDER", "Scheduler stopped.")
            except Exception as e:
                logger.debug("REMINDER", f"Scheduler stop error: {e}")
            _scheduler = None


def add_job(reminder: dict) -> bool:
    """
    Schedules a reminder job using the stored when_iso (DateTrigger) or
    cron_expr (CronTrigger). Returns True on success.
    :param reminder: dict from store — must include 'id', 'when_iso', 'cron_expr', 'repeat'.
    """
    if not APSCHEDULER_AVAILABLE or _scheduler is None:
        return False

    reminder_id = reminder.get("id")
    title       = reminder.get("title", "")
    when_iso    = reminder.get("when_iso")
    cron_expr   = reminder.get("cron_expr")
    is_repeat   = bool(reminder.get("repeat", 0))

    try:
        # Build the trigger
        if is_repeat and cron_expr:
            trigger = _cron_from_expr(cron_expr)
        elif when_iso:
            dt = datetime.fromisoformat(when_iso)
            if dt <= datetime.now():
                logger.debug("REMINDER", f"Skipping past reminder [{reminder_id}] '{title}'")
                return False
            trigger = DateTrigger(run_date=dt)
        else:
            logger.debug("REMINDER", f"No trigger info for [{reminder_id}] — skipped.")
            return False

        job_id = _job_id(reminder_id)

        # Remove stale job if exists
        if _scheduler.get_job(job_id):
            _scheduler.remove_job(job_id)

        _scheduler.add_job(
            func=_fire_callback,
            trigger=trigger,
            id=job_id,
            name=f"Reminder: {title}",
            args=[reminder_id],
            misfire_grace_time=300,  # 5 min grace — handles system sleep/wake
            coalesce=True,
        )
        logger.debug("REMINDER", f"Job scheduled: [{reminder_id}] '{title}'")
        return True

    except Exception as e:
        logger.error(f"[REMINDER] add_job error for [{reminder_id}]: {e}")
        return False


def cancel_job(reminder_id: str) -> bool:
    """Removes the APScheduler job for this reminder. Returns True on success."""
    if not APSCHEDULER_AVAILABLE or _scheduler is None:
        return False
    try:
        job_id = _job_id(reminder_id)
        if _scheduler.get_job(job_id):
            _scheduler.remove_job(job_id)
            logger.debug("REMINDER", f"Job cancelled: [{reminder_id}]")
        return True
    except Exception as e:
        logger.error(f"[REMINDER] cancel_job error: {e}")
        return False


def reschedule_job(reminder_id: str, new_iso: str) -> bool:
    """
    Reschedules a job to a new datetime (used for snooze).
    :param new_iso: New ISO 8601 datetime string.
    """
    if not APSCHEDULER_AVAILABLE or _scheduler is None:
        return False
    try:
        dt = datetime.fromisoformat(new_iso)
        job_id = _job_id(reminder_id)
        if _scheduler.get_job(job_id):
            _scheduler.reschedule_job(job_id, trigger=DateTrigger(run_date=dt))
        else:
            # Job was already fired/removed — re-add with new trigger
            from hecos.plugins.reminder import store
            reminder = store.get_by_id(reminder_id)
            if reminder:
                reminder["when_iso"] = new_iso
                reminder["repeat"] = 0
                add_job(reminder)
        logger.debug("REMINDER", f"Job rescheduled: [{reminder_id}] → {new_iso}")
        return True
    except Exception as e:
        logger.error(f"[REMINDER] reschedule_job error: {e}")
        return False


def _reload_from_db() -> None:
    """Loads all active reminders from store and schedules them."""
    try:
        from hecos.plugins.reminder import store
        reminders = store.get_all(status_filter="active")
        count = 0
        for r in reminders:
            if add_job(r):
                count += 1
        logger.info("REMINDER", f"Loaded {count}/{len(reminders)} reminders from DB.")
    except Exception as e:
        logger.error(f"[REMINDER] _reload_from_db error: {e}")


def _cron_from_expr(cron_expr: str) -> "CronTrigger":
    """
    Builds a CronTrigger from a stored CRON expression string.
    The stored format is 'min hour day month day_of_week' (5 fields, space-separated).
    """
    parts = cron_expr.strip().split()
    if len(parts) == 5:
        return CronTrigger(
            minute=parts[0], hour=parts[1], day=parts[2],
            month=parts[3], day_of_week=parts[4]
        )
    # Fallback: treat as kwargs string 'key=val key=val ...'
    kwargs = dict(kv.split("=") for kv in parts if "=" in kv)
    return CronTrigger(**kwargs)


def get_status() -> dict:
    """Returns diagnostic info about the scheduler state."""
    if not APSCHEDULER_AVAILABLE or _scheduler is None:
        return {"running": False, "jobs": 0}
    jobs = _scheduler.get_jobs()
    return {
        "running": _scheduler.running,
        "jobs":    len(jobs),
        "job_ids": [j.id for j in jobs],
    }
