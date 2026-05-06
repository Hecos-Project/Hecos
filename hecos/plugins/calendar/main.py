"""
MODULE: Calendar Plugin — LLM Tools
DESCRIPTION: Exposes add_event, list_events, delete_event as Hecos LLM tools.
             Loaded at boot via plugin manifest (is_class_based: true, on_load: true).
"""

import os
from datetime import datetime, timedelta
from hecos.core.logging import logger


class CalendarTools:
    """Hecos Calendar plugin — exposes all calendar LLM tools."""

    def __init__(self, config_manager=None):
        self._cfg = config_manager
        self.tag = "CALENDAR"

    # ── LLM Tools ─────────────────────────────────────────────────────────────

    def add_event(self, title: str, start: str, end: str = None,
                  all_day: bool = False, notes: str = None, color: str = None) -> str:
        """Creates a new calendar event. Returns a confirmation string."""
        from hecos.plugins.calendar import store
        try:
            start_iso = self._parse_date(start)
            if start_iso is None:
                return f"⚠️ I could not understand the date: '{start}'. Please use a clear format like 'tomorrow at 10:00' or '2026-06-01 14:30'."

            end_iso = None
            if end:
                end_iso = self._parse_date(end)
            elif not all_day and start_iso:
                # Default 1-hour duration
                from datetime import datetime, timedelta
                dt = datetime.fromisoformat(start_iso)
                end_iso = (dt + timedelta(hours=1)).isoformat()

            event = store.add(
                title=title,
                start_iso=start_iso,
                end_iso=end_iso,
                all_day=all_day,
                color=color,
                notes=notes
            )
            start_fmt = self._fmt_date(start_iso)
            return f"📅 Event added: **{title}** on {start_fmt}. (ID: `{event['id'][:8]}`)"
        except Exception as e:
            logger.debug("CALENDAR", f"add_event error: {e}")
            return f"⚠️ Failed to add event: {e}"

    def list_events(self, n: int = 10) -> str:
        """Returns a formatted list of upcoming calendar events."""
        from hecos.plugins.calendar import store
        try:
            events = store.get_upcoming(n)
            if not events:
                return "📅 No upcoming calendar events."
            lines = ["📅 **Upcoming Calendar Events:**"]
            for ev in events:
                start_fmt = self._fmt_date(ev["start_iso"])
                note_txt = f" — {ev['notes']}" if ev.get("notes") else ""
                lines.append(f"• **{ev['title']}** | {start_fmt}{note_txt} _(ID: {ev['id'][:8]})_")
            return "\n".join(lines)
        except Exception as e:
            logger.debug("CALENDAR", f"list_events error: {e}")
            return f"⚠️ Failed to list events: {e}"

    def delete_event(self, event_id: str) -> str:
        """Deletes a calendar event by ID."""
        from hecos.plugins.calendar import store
        try:
            ev = store.get_by_id(event_id)
            if not ev:
                return f"⚠️ No event found with ID '{event_id}'. Use `list_events` to see IDs."
            title = ev["title"]
            deleted = store.delete(event_id)
            if deleted:
                return f"🗑️ Event **{title}** has been deleted."
            return f"⚠️ Could not delete event '{event_id}'."
        except Exception as e:
            logger.debug("CALENDAR", f"delete_event error: {e}")
            return f"⚠️ Failed to delete event: {e}"

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _parse_date(self, when: str) -> str | None:
        """Parses a natural language or ISO date string to ISO format string."""
        if not when:
            return None
        try:
            import dateparser
            dt = dateparser.parse(
                when,
                settings={
                    "PREFER_DATES_FROM": "future",
                    "RETURN_AS_TIMEZONE_AWARE": False,
                    "LANGUAGES": ["en", "it"],
                }
            )
            if dt:
                return dt.strftime("%Y-%m-%dT%H:%M:%S")
        except ImportError:
            pass
        # Fallback: try standard ISO
        try:
            return datetime.fromisoformat(when).isoformat()
        except Exception:
            return None

    def _fmt_date(self, iso: str) -> str:
        """Formats an ISO date string for display."""
        try:
            dt = datetime.fromisoformat(iso)
            return dt.strftime("%A %d %B %Y at %H:%M")
        except Exception:
            return iso


# ── Singleton ──────────────────────────────────────────────────────────────────
tools = CalendarTools()
