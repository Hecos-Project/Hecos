"""
MODULE: Reminder Plugin — Main Entry Point
DESCRIPTION: Exposes ReminderTools to the Hecos agent loop.
             Tools: set_reminder, list_reminders, cancel_reminder, snooze_reminder.
             Starts the APScheduler daemon on on_load().
"""

from datetime import datetime, timedelta
from hecos.core.logging import logger

try:
    from hecos.core.i18n import translator
except ImportError:
    class _DummyTranslator:
        def t(self, key, **kwargs): return key
    translator = _DummyTranslator()

from hecos.plugins.reminder import store, scheduler, parser


class ReminderTools:
    """
    Hecos Reminder Plugin — schedule, list, cancel and snooze reminders.
    Supports natural language time expressions and CRON-style recurrence.
    """

    def __init__(self):
        self.tag    = "REMINDER"
        self.desc   = "Scheduler for time-based reminders with TTS alerts and WebUI notifications."
        self.status = "ONLINE"
        self.stop_flag = False

        self.config_schema = {
            "reminder_mode": {
                "type": "str",
                "default": "voice",
                "options": ["voice", "ringtone", "both"],
                "description": "How alerts are played: voice (TTS), ringtone, or both."
            },
            "ringtone_path": {
                "type": "str",
                "default": "",
                "description": "Absolute path to a custom audio file (.wav, .mp3) to play. Note: Hecos must have read access."
            },
            "time_format": {
                "type": "str",
                "default": "24h",
                "options": ["12h", "24h"],
                "description": "Display format for reminder times."
            },
            "max_reminders": {
                "type": "int",
                "default": 50,
                "description": "Maximum number of active reminders allowed."
            },
            "snooze_default_minutes": {
                "type": "int",
                "default": 15,
                "description": "Default snooze duration in minutes."
            },
            "reminder_snooze_ui": {
                "type": "bool",
                "default": False,
                "description": "If enabled, reminder audio loops continuously until dismissed or snoozed."
            }
        }

    # ── Public Tools ──────────────────────────────────────────────────────────

    def set_reminder(self, title: str, when: str, repeat: str = None, interactive: bool = None) -> str:
        """
        Creates a new reminder. Fires a TTS alert and WebUI notification when due.
        :param title: What to remind the user about (e.g. 'Call the doctor').
        :param when: The scheduled time. **CRITICAL**: Use your native intelligence to calculate the 
                     exact Target Date/Time based on the user's request and the current time. 
                     Return it STRCITLY as 'YYYY-MM-DD HH:MM' or a clean 'in X minutes'.
                     Only if the user uses an extremely ambiguous request, pass exactly what they said.
        :param repeat: Optional override CRON expression (e.g. '0 9 * * 1').
                       If omitted, `when` is parsed for recurrence automatically.
        :param interactive: True = interactive snooze (alarm loops, banner with Snooze/Stop buttons).
                            False = simple (plays once, banner auto-dismisses on interaction).
                            None (default) = use the system default setting from config.
        """
        # Determine trigger
        cron_expr = None
        when_iso  = None
        is_repeat = False

        if repeat:
            cron_expr = repeat
            is_repeat = True
            trigger_type = "cron"
        else:
            trigger_type, trigger_value = parser.smart_parse(when)

            if trigger_type == "cron":
                tf = trigger_value.fields
                field_map = {f.name: str(f) for f in tf}
                cron_expr = " ".join([
                    field_map.get("minute", "*"),
                    field_map.get("hour", "*"),
                    field_map.get("day", "*"),
                    field_map.get("month", "*"),
                    field_map.get("day_of_week", "*"),
                ])
                is_repeat = True

            elif trigger_type == "date":
                when_iso = trigger_value.isoformat()

            else:
                return translator.t("ext_reminder_parse_err", when=when)

        # Check capacity
        active = store.get_all(status_filter="active")
        if len(active) >= 50:
            return translator.t("ext_reminder_limit_err")

        # Store
        reminder = store.add(
            title=title,
            when_iso=when_iso,
            cron_expr=cron_expr,
            repeat=is_repeat,
            interactive=interactive
        )

        # Schedule
        scheduled = scheduler.add_job(reminder)

        # Build response
        if trigger_type == "date":
            dt = datetime.fromisoformat(when_iso)
            at_word = translator.t("ext_reminder_at")
            time_str = dt.strftime(f"%d/%m/%Y {at_word} %H:%M")
            sched_info = f"📅 {time_str}"
        elif trigger_type == "cron":
            recurrent_word = translator.t("ext_reminder_recurrent")
            sched_info = f"🔁 {recurrent_word} ({when})"
        else:
            sched_info = when

        if scheduled:
            logger.info("REMINDER", f"Set: '{title}' — {sched_info}")
            msg = translator.t("ext_reminder_set_success")
            short_id = reminder['id'][:8]
            return (
                f"{msg}\n"
                f"📌 **{title}**\n"
                f"⏰ {sched_info}\n"
                f"🆔 ID: `{short_id}...`"
            )
        else:
            msg = translator.t("ext_reminder_set_error")
            short_id = reminder['id'][:8]
            return f"{msg} ID: `{short_id}...`"

    def list_reminders(self) -> str:
        """
        Lists all active reminders with their scheduled time and ID.
        """
        reminders = store.get_all(status_filter="active")
        if not reminders:
            return translator.t("ext_reminder_none")

        lines = [f"{translator.t('ext_reminder_list_title')}\n"]
        for r in reminders:
            short_id = r["id"][:8]
            if r.get("repeat") and r.get("cron_expr"):
                time_info = f"🔁 `{r['cron_expr']}`"
            elif r.get("when_iso"):
                try:
                    dt = datetime.fromisoformat(r["when_iso"])
                    time_info = dt.strftime("📅 %d/%m/%Y %H:%M")
                except Exception:
                    time_info = r["when_iso"]
            else:
                time_info = translator.t("ext_reminder_unknown_date")

            lines.append(f"• **{r['title']}** — {time_info} — ID: `{short_id}`")

        return "\n".join(lines)

    def cancel_reminder(self, reminder_id: str) -> str:
        """
        Cancels an active reminder by its ID (full or first-8-chars prefix).
        :param reminder_id: The ID (or first 8 characters) shown in list_reminders().
        """
        # Support short IDs (first 8 chars)
        reminder = _resolve_id(reminder_id)
        if not reminder:
            return translator.t("ext_reminder_not_found", id=reminder_id)

        rid = reminder["id"]
        scheduler.cancel_job(rid)
        store.cancel(rid)
        logger.info("REMINDER", f"Cancelled: [{rid}] '{reminder['title']}'")
        return translator.t("ext_reminder_cancelled", title=reminder["title"])

    def snooze_reminder(self, reminder_id: str, minutes: int = 15) -> str:
        """
        Postpones a reminder by the specified number of minutes from now.
        :param reminder_id: The ID (or first 8 characters) of the reminder to snooze.
        :param minutes: How many minutes to postpone (default: 15).
        """
        reminder = _resolve_id(reminder_id)
        if not reminder:
            return translator.t("ext_reminder_not_found", id=reminder_id)

        rid = reminder["id"]
        new_dt  = datetime.now() + timedelta(minutes=int(minutes))
        new_iso = new_dt.isoformat()

        store.update_when(rid, new_iso)
        scheduler.reschedule_job(rid, new_iso)

        time_str = new_dt.strftime("%H:%M")
        logger.info("REMINDER", f"Snoozed: [{rid}] '{reminder['title']}' → {new_iso}")
        self.stop_audio()  # Stop currently ringing alarm
        return translator.t("ext_reminder_snoozed", title=reminder["title"], time=time_str)

    def stop_audio(self) -> str:
        """
        Signals the notifier to stop any currently playing or looping audio.
        """
        self.stop_flag = True
        logger.info("REMINDER", "Audio loop interrupted by user.")
        return "Audio stopped."


# ── Helpers ───────────────────────────────────────────────────────────────────

def _resolve_id(reminder_id: str) -> dict | None:
    """Matches a full UUID or an 8-char prefix against active reminders."""
    reminder_id = reminder_id.strip()
    # Try exact match first
    r = store.get_by_id(reminder_id)
    if r:
        return r
    # Try prefix match
    all_active = store.get_all(status_filter="active")
    for r in all_active:
        if r["id"].startswith(reminder_id):
            return r
    return None


# ── Singleton ─────────────────────────────────────────────────────────────────
tools = ReminderTools()


def info():
    return {"tag": tools.tag, "desc": tools.desc}


def status():
    return tools.status


def on_load(config: dict = None):
    """Called by the plugin loader when Hecos starts. Starts the scheduler daemon."""
    scheduler.start()
    logger.info("REMINDER", "Plugin loaded — scheduler running.")
