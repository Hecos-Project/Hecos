"""
MODULE: Reminder Parser
DESCRIPTION: Natural language datetime and CRON expression parsing.
             Uses dateparser for human-readable time expressions and
             maps recurring patterns to APScheduler CronTrigger.
"""

import re
from datetime import datetime, timedelta
from typing import Tuple, Any
from hecos.core.logging import logger

# ── Dateparser (optional, with graceful fallback) ─────────────────────────────
try:
    import dateparser
    DATEPARSER_AVAILABLE = True
except ImportError:
    DATEPARSER_AVAILABLE = False
    logger.debug("REMINDER", "dateparser not installed — falling back to basic time parser.")

# ── APScheduler triggers ──────────────────────────────────────────────────────
try:
    from apscheduler.triggers.date import DateTrigger
    from apscheduler.triggers.cron import CronTrigger
    APSCHEDULER_AVAILABLE = True
except ImportError:
    APSCHEDULER_AVAILABLE = False

# ── CRON Pattern Map ──────────────────────────────────────────────────────────
# Maps common Italian/English recurring expressions to CRON fields.
# Format: (regex, {minute, hour, day, month, day_of_week})
_CRON_PATTERNS = [
    # "ogni giorno alle HH:MM" / "ogni giorno alle H"
    (r"(?:ogni giorno|ogni giorno|daily|every day)(?:.*?alle?\s+(\d{1,2})(?::(\d{2}))?)?",
     lambda m: {"hour": m.group(1) or "8", "minute": m.group(2) or "0",
                "day": "*", "month": "*", "day_of_week": "*"}),

    # "ogni lunedì/martedì/.../domenica alle HH:MM"
    (r"ogni\s+(lunedì|martedì|mercoledì|giovedì|venerdì|sabato|domenica|"
     r"monday|tuesday|wednesday|thursday|friday|saturday|sunday)"
     r"(?:.*?alle?\s+(\d{1,2})(?::(\d{2}))?)?",
     lambda m: {
         "day_of_week": {
             "lunedì": "mon", "martedì": "tue", "mercoledì": "wed",
             "giovedì": "thu", "venerdì": "fri", "sabato": "sat", "domenica": "sun",
             "monday": "mon", "tuesday": "tue", "wednesday": "wed",
             "thursday": "thu", "friday": "fri", "saturday": "sat", "sunday": "sun",
         }.get(m.group(1).lower(), "mon"),
         "hour": m.group(2) or "9",
         "minute": m.group(3) or "0",
         "day": "*", "month": "*"
     }),

    # "ogni settimana" / "every week" (defaults: Monday 9:00)
    (r"ogni settimana|every week",
     lambda m: {"day_of_week": "mon", "hour": "9", "minute": "0",
                "day": "*", "month": "*"}),

    # "ogni mese" / "every month" / "ogni primo del mese" (1st at 9:00)
    (r"ogni (?:primo del |)mese|every month|monthly",
     lambda m: {"day": "1", "hour": "9", "minute": "0",
                "month": "*", "day_of_week": "*"}),

    # "ogni ora" / "every hour"
    (r"ogni ora|every hour|hourly",
     lambda m: {"minute": "0", "hour": "*", "day": "*",
                "month": "*", "day_of_week": "*"}),

    # "ogni mattina" / "every morning" → 8:00
    (r"ogni mattina|every morning",
     lambda m: {"hour": "8", "minute": "0", "day": "*",
                "month": "*", "day_of_week": "*"}),

    # "ogni sera" / "every evening" → 20:00
    (r"ogni sera|every evening",
     lambda m: {"hour": "20", "minute": "0", "day": "*",
                "month": "*", "day_of_week": "*"}),

    # Raw CRON expression (5 fields: min hour day month dow)
    (r"^(\d+|\*)\s+(\d+|\*)\s+(\d+|\*)\s+(\d+|\*)\s+(\d+|\*|\w+)$",
     lambda m: {"minute": m.group(1), "hour": m.group(2), "day": m.group(3),
                "month": m.group(4), "day_of_week": m.group(5)}),
]


def _extract_time_from_cron_text(text: str) -> Tuple[str, str]:
    """Extracts hour and minute from expressions like 'alle 15:30' or 'alle 9'."""
    m = re.search(r"alle?\s+(\d{1,2})(?::(\d{2}))?", text, re.IGNORECASE)
    if m:
        return m.group(1), (m.group(2) or "0")
    return "9", "0"


def parse_cron(text: str) -> Any:
    """
    Tries to match `text` against known recurring patterns.
    Returns an APScheduler CronTrigger on match, or None.
    """
    if not APSCHEDULER_AVAILABLE:
        return None

    text_lower = text.lower().strip()
    for pattern, builder in _CRON_PATTERNS:
        m = re.search(pattern, text_lower, re.IGNORECASE)
        if m:
            try:
                kwargs = builder(m)
                trigger = CronTrigger(**kwargs)
                logger.debug("REMINDER", f"CRON match: '{text}' → {kwargs}")
                return trigger
            except Exception as e:
                logger.debug("REMINDER", f"CronTrigger build error for '{text}': {e}")
    return None


def parse_datetime(text: str) -> datetime | None:
    """
    Parses a natural language datetime string.
    Supports: "domani alle 15", "tra 20 minuti", "15 maggio alle 9",
              "venerdì alle 18:30", "2025-05-10 14:00", etc.
    Returns a datetime (timezone-naive, local time) or None on failure.
    """
    if not text:
        return None

    if DATEPARSER_AVAILABLE:
        settings = {
            "PREFER_DATES_FROM": "future",
            "RETURN_AS_TIMEZONE_AWARE": False,
            "PARSERS": [
                "relative-time", "absolute-time",
                "custom-formats", "no-spaces-time", "timestamp"
            ],
        }
        try:
            result = dateparser.parse(text, settings=settings, languages=["it", "en"])
            if result:
                # Reject dates in the past (allow 10s tolerance)
                if result < datetime.now() - timedelta(seconds=10):
                    logger.debug("REMINDER", f"Parsed datetime is in the past: {result}")
                    return None
                return result
        except Exception as e:
            logger.debug("REMINDER", f"dateparser error: {e}")

    # ── Basic fallback parser (no dateparser) ─────────────────────────────────
    return _basic_parse(text)


def _basic_parse(text: str) -> datetime | None:
    """Minimal fallback parser for simple expressions when dateparser is unavailable or fails."""
    text_lower = text.lower().strip()
    now = datetime.now()

    # Map common Italian word-numbers to digits to fortify the fallback
    text_lower = re.sub(r"\bun['’一]?", "1 ", text_lower)
    replacements = {
        r"\b(?:uno|una)\b": "1", r"\bdue\b": "2", r"\btre\b": "3", r"\bquattro\b": "4",
        r"\bcinque\b": "5", r"\bsei\b": "6", r"\bsette\b": "7", r"\botto\b": "8",
        r"\bnove\b": "9", r"\bdieci\b": "10", r"\bundici\b": "11", r"\bdodici\b": "12",
        r"\bquindici\b": "15", r"\bventi\b": "20", r"\bmezz'ora\b": "30 minut", r"\bmezzora\b": "30 minut"
    }
    for pat, rep in replacements.items():
        text_lower = re.sub(pat, rep, text_lower)

    # "(tra) N minuti"
    m = re.search(r"(?:(?:tra|fra|in)\s+)?(\d+)\s*minut", text_lower)
    if m:
        return now + timedelta(minutes=int(m.group(1)))

    # "(tra) N ore"
    m = re.search(r"(?:(?:tra|fra|in)\s+)?(\d+)\s*or[ae]", text_lower)
    if m:
        return now + timedelta(hours=int(m.group(1)))

    # "HH:MM" (today, if in future; tomorrow otherwise)
    m = re.search(r"\b(\d{1,2}):(\d{2})\b", text_lower)
    if m:
        candidate = now.replace(hour=int(m.group(1)), minute=int(m.group(2)), second=0, microsecond=0)
        if candidate <= now:
            candidate += timedelta(days=1)
        return candidate

    # "alle H" (hours only)
    m = re.search(r"alle?\s+(\d{1,2})", text_lower)
    if m:
        candidate = now.replace(hour=int(m.group(1)), minute=0, second=0, microsecond=0)
        if candidate <= now:
            candidate += timedelta(days=1)
        return candidate

    return None


def smart_parse(text: str) -> Tuple[str, Any]:
    """
    Determines whether `text` describes a one-shot or recurring reminder.
    Returns ("cron", CronTrigger) or ("date", datetime) or ("unknown", None).
    """
    # Check recurring patterns first
    cron_trigger = parse_cron(text)
    if cron_trigger:
        return "cron", cron_trigger

    # Fall back to one-shot datetime
    dt = parse_datetime(text)
    if dt:
        return "date", dt

    return "unknown", None
