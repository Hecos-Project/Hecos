"""
MODULE: Reminder Notifier
DESCRIPTION: Fires a reminder alert.
             On trigger:
             1. TTS via core/audio/voice.py speak() — runs in a daemon thread
             2. StateManager.add_event("reminder_fire") → WebUI SSE banner
"""

import threading
from hecos.core.logging import logger


def fire_reminder(reminder: dict) -> None:
    """
    Dispatches a reminder alert. Called by the APScheduler worker thread.
    :param reminder: dict from store (id, title, when_iso, cron_expr, repeat, status)
    """
    title = reminder.get("title", "Promemoria")
    reminder_id = reminder.get("id", "")
    is_repeat = bool(reminder.get("repeat", 0))

    logger.info("REMINDER", f"🔔 FIRE: [{reminder_id}] '{title}'")

    # ── 1. TTS Alert ─────────────────────────────────────────────────────────
    # speak() is blocking (Piper subprocess + audio playback).
    # We run it in a daemon thread so the scheduler is not blocked.
    def _speak_async():
        try:
            from hecos.core.audio.voice import speak
            speak(f"Promemoria: {title}")
        except Exception as e:
            logger.debug("REMINDER", f"TTS alert error: {e}")

    tts_thread = threading.Thread(target=_speak_async, daemon=True, name=f"reminder-tts-{reminder_id}")
    tts_thread.start()

    # ── 2. WebUI SSE Push ─────────────────────────────────────────────────────
    # StateManager.add_event() is thread-safe (uses a lock internally).
    # The WebUI /api/events SSE stream already polls pop_events() every ~500ms.
    # chat_events.js listens and will display a banner on "reminder_fire" events.
    try:
        from hecos.modules.web_ui.server import get_state_manager
        sm = get_state_manager()
        if sm is not None:
            sm.add_event("reminder_fire", {
                "id":    reminder_id,
                "title": title,
            })
            logger.debug("REMINDER", f"SSE event pushed for reminder [{reminder_id}]")
        else:
            logger.debug("REMINDER", "StateManager not available — WebUI push skipped.")
    except Exception as e:
        logger.debug("REMINDER", f"WebUI push error: {e}")

    # ── 3. Mark as fired (one-shot only; recurring stays active) ──────────────
    if not is_repeat:
        try:
            from hecos.plugins.reminder import store
            store.update_status(reminder_id, "fired")
        except Exception as e:
            logger.debug("REMINDER", f"Store update error after fire: {e}")
