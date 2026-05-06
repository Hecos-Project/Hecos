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

    # ── 1. TTS / Ringtone Alert ──────────────────────────────────────────────
    # We run it in a daemon thread so the scheduler is not blocked.
    def _alert_async():
        from hecos.app.config import ConfigManager
        config = ConfigManager().config
        plugin_config = config.get("plugins", {}).get("REMINDER", {})
        
        mode = plugin_config.get("reminder_mode", "voice").lower()
        ringtone_path = plugin_config.get("ringtone_path", "").strip()

        # Ringtone
        if mode in ("ringtone", "both"):
            try:
                import os
                import subprocess
                
                final_path = ""
                if ringtone_path:
                    if os.path.isabs(ringtone_path) and os.path.exists(ringtone_path):
                        final_path = ringtone_path
                    else:
                        _base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
                        _test_path = os.path.join(_base, "assets", "sounds", ringtone_path)
                        if os.path.exists(_test_path):
                            final_path = _test_path
                
                # Fallback to system default if no path or file not found
                if not final_path:
                    _base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
                    final_path = os.path.join(_base, "assets", "sounds", "Default_System_Alert.mp3")

                if os.path.exists(final_path):
                    if final_path.lower().endswith(".wav"):
                        import winsound
                        winsound.PlaySound(final_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
                    else:
                        # Use PowerShell for MP3/others on Windows
                        # We use a non-blocking background command
                        # We escape single quotes for PowerShell
                        safe_path = final_path.replace("'", "''")
                        ps_cmd = (
                            f"Add-Type -AssemblyName PresentationCore; "
                            f"$p = New-Object System.Windows.Media.MediaPlayer; "
                            f"$p.Open('{safe_path}'); "
                            f"for($i=0; $i -lt 20; $i++) {{ if($p.DownloadProgress -ge 1 -or $p.NaturalDuration.HasTimeSpan) {{ break }}; Start-Sleep -m 100 }}; "
                            f"$p.Play(); "
                            f"Start-Sleep -s 15; $p.Stop();"
                        )
                        subprocess.Popen(["powershell", "-Command", ps_cmd], 
                                         creationflags=subprocess.CREATE_NO_WINDOW)
            except Exception as e:
                logger.debug("REMINDER", f"Ringtone error: {e}")

        # TTS Voice
        if mode in ("voice", "both"):
            try:
                from hecos.core.audio.voice import speak
                speak(f"Reminder: {title}")
            except Exception as e:
                logger.debug("REMINDER", f"TTS alert error: {e}")

    tts_thread = threading.Thread(target=_alert_async, daemon=True, name=f"reminder-alert-{reminder_id}")
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
