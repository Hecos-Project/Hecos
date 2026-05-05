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

        self.config_schema = {
            "tts_enabled": {
                "type": "bool",
                "default": True,
                "description": "Play a TTS voice alert when a reminder fires."
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
            }
        }

    # ── Public Tools ──────────────────────────────────────────────────────────

    def set_reminder(self, title: str, when: str, repeat: str = None) -> str:
        """
        Creates a new reminder. Fires a TTS alert and WebUI notification when due.
        :param title: What to remind the user about (e.g. 'Call the doctor').
        :param when: When to fire the reminder. Accepts natural language like
                     'tomorrow at 15:00', 'in 20 minutes', 'every Monday at 9:00',
                     'ogni giorno alle 8', 'tra 30 minuti'.
        :param repeat: Optional override CRON expression (e.g. '0 9 * * 1').
                       If omitted, `when` is parsed for recurrence automatically.
        """
        # Determine trigger
        cron_expr = None
        when_iso  = None
        is_repeat = False

        if repeat:
            # Explicit CRON override
            cron_expr = repeat
            is_repeat = True
            trigger_type = "cron"
        else:
            trigger_type, trigger_value = parser.smart_parse(when)

            if trigger_type == "cron":
                # Serialise CronTrigger fields to '5-field' string for storage
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
                return (
                    f"[REMINDER] ❌ Non riesco a interpretare '{when}'. "
                    "Prova con: 'domani alle 15', 'tra 30 minuti', 'ogni lunedì alle 9'."
                )

        # Check capacity
        active = store.get_all(status_filter="active")
        if len(active) >= 50:
            return "[REMINDER] ❌ Limite massimo di promemoria attivi raggiunto (50)."

        # Store
        reminder = store.add(
            title=title,
            when_iso=when_iso,
            cron_expr=cron_expr,
            repeat=is_repeat
        )

        # Schedule
        scheduled = scheduler.add_job(reminder)

        # Build response
        if trigger_type == "date":
            dt = datetime.fromisoformat(when_iso)
            time_str = dt.strftime("%d/%m/%Y alle %H:%M")
            sched_info = f"📅 {time_str}"
        elif trigger_type == "cron":
            sched_info = f"🔁 ricorrente ({when})"
        else:
            sched_info = when

        if scheduled:
            logger.info("REMINDER", f"Set: '{title}' — {sched_info}")
            return (
                f"✅ Promemoria impostato!\n"
                f"📌 **{title}**\n"
                f"⏰ {sched_info}\n"
                f"🆔 ID: `{reminder['id'][:8]}...`"
            )
        else:
            return (
                f"⚠️ Promemoria salvato nel database ma non schedulato "
                f"(APScheduler potrebbe non essere disponibile). "
                f"ID: `{reminder['id'][:8]}...`"
            )

    def list_reminders(self) -> str:
        """
        Lists all active reminders with their scheduled time and ID.
        """
        reminders = store.get_all(status_filter="active")
        if not reminders:
            return "📭 Nessun promemoria attivo."

        lines = ["📋 **Promemoria attivi:**\n"]
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
                time_info = "❓ data sconosciuta"

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
            return f"[REMINDER] ❌ Nessun promemoria trovato con ID `{reminder_id}`."

        rid = reminder["id"]
        scheduler.cancel_job(rid)
        store.cancel(rid)
        logger.info("REMINDER", f"Cancelled: [{rid}] '{reminder['title']}'")
        return f"🗑️ Promemoria **{reminder['title']}** cancellato."

    def snooze_reminder(self, reminder_id: str, minutes: int = 15) -> str:
        """
        Postpones a reminder by the specified number of minutes from now.
        :param reminder_id: The ID (or first 8 characters) of the reminder to snooze.
        :param minutes: How many minutes to postpone (default: 15).
        """
        reminder = _resolve_id(reminder_id)
        if not reminder:
            return f"[REMINDER] ❌ Nessun promemoria trovato con ID `{reminder_id}`."

        rid = reminder["id"]
        new_dt  = datetime.now() + timedelta(minutes=int(minutes))
        new_iso = new_dt.isoformat()

        store.update_when(rid, new_iso)
        scheduler.reschedule_job(rid, new_iso)

        time_str = new_dt.strftime("%H:%M")
        logger.info("REMINDER", f"Snoozed: [{rid}] '{reminder['title']}' → {new_iso}")
        return f"💤 Promemoria **{reminder['title']}** posticipato alle {time_str}."


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
