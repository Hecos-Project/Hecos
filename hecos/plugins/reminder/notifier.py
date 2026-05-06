"""
MODULE: Reminder Notifier
DESCRIPTION: Fires a reminder alert.
             On trigger:
             1. TTS via core/audio/voice.py speak() — runs in a daemon thread
             2. StateManager.add_event("reminder_fire") → WebUI SSE banner
"""

import os
import threading
import time
from hecos.core.logging import logger

try:
    from hecos.core.i18n import translator
except ImportError:
    class _DummyTranslator:
        def t(self, key, **kwargs): return key
    translator = _DummyTranslator()


# Resolve assets/sounds directory relative to this file:
# notifier.py is at hecos/plugins/reminder/notifier.py
# assets/sounds is at   hecos/assets/sounds/
_SOUNDS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "assets", "sounds"))


def _resolve_ringtone(ringtone_path: str) -> str:
    """Returns the absolute path to the ringtone file, or empty string if not found."""
    if ringtone_path:
        # Absolute path supplied — use directly if it exists
        if os.path.isabs(ringtone_path) and os.path.exists(ringtone_path):
            return ringtone_path
        # Relative name — look in assets/sounds/
        candidate = os.path.join(_SOUNDS_DIR, ringtone_path)
        if os.path.exists(candidate):
            return candidate

    # Fallback to built-in default
    default = os.path.join(_SOUNDS_DIR, "Default_System_Alert.mp3")
    if os.path.exists(default):
        return default

    logger.debug("REMINDER", f"Ringtone not found. Searched: '{ringtone_path}' in '{_SOUNDS_DIR}'")
    return ""


def _play_ringtone_once(path: str, stop_check=None) -> None:
    """
    Plays a ringtone file synchronously (blocks until playback ends or stop_check returns True).
    stop_check: optional callable that returns True to abort playback.
    """
    if not path or not os.path.exists(path):
        logger.debug("REMINDER", f"Ringtone file not found, skipping playback: '{path}'")
        return

    try:
        import sys, subprocess

        if sys.platform == "win32":
            if path.lower().endswith(".wav"):
                import winsound
                winsound.PlaySound(path, winsound.SND_FILENAME)
                return
            else:
                safe_path = path.replace("'", "''")
                ps_cmd = (
                    f"Add-Type -AssemblyName PresentationCore; "
                    f"$p = New-Object System.Windows.Media.MediaPlayer; "
                    f"$p.Open('{safe_path}'); "
                    f"for($i=0; $i -lt 30; $i++) {{ if($p.NaturalDuration.HasTimeSpan) {{ break }}; Start-Sleep -m 100 }}; "
                    f"$p.Play(); "
                    f"while ($p.Position -lt $p.NaturalDuration.TimeSpan) {{ Start-Sleep -m 100 }}"
                )
                proc = subprocess.Popen(
                    ["powershell", "-Command", ps_cmd],
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
        elif sys.platform == "darwin":
            proc = subprocess.Popen(["afplay", path])
        else:
            import shutil
            if shutil.which("paplay"):
                proc = subprocess.Popen(["paplay", path])
            elif shutil.which("ffplay"):
                proc = subprocess.Popen(["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", path])
            elif shutil.which("aplay") and path.lower().endswith(".wav"):
                proc = subprocess.Popen(["aplay", path])
            else:
                logger.debug("REMINDER", "No supported audio player found on Linux.")
                return

        while proc.poll() is None:
            if stop_check and stop_check():
                proc.kill()
                break
            time.sleep(0.2)
    except Exception as e:
        logger.debug("REMINDER", f"Ringtone playback error: {e}")


def fire_reminder(reminder: dict) -> None:
    """
    Dispatches a reminder alert. Called by the APScheduler worker thread.
    :param reminder: dict from store (id, title, when_iso, cron_expr, repeat, status)
    """
    title = reminder.get("title", "Reminder")
    reminder_id = reminder.get("id", "")
    is_repeat = bool(reminder.get("repeat", 0))

    logger.info("REMINDER", f"🔔 FIRE: [{reminder_id}] '{title}'")

    def _alert_async():
        from hecos.app.config import ConfigManager
        plugin_config = ConfigManager().config.get("plugins", {}).get("REMINDER", {})

        mode = plugin_config.get("reminder_mode", "voice").lower()
        ringtone_path = plugin_config.get("ringtone_path", "").strip()

        # Per-reminder interactive setting overrides system default
        r_interactive = reminder.get("interactive")  # 1, 0, or None
        if r_interactive is None:
            snooze_enabled = plugin_config.get("reminder_snooze_ui", False)
        else:
            snooze_enabled = bool(r_interactive)

        from hecos.plugins.reminder.main import tools
        tools.stop_flag = False

        resolved = _resolve_ringtone(ringtone_path)
        logger.info("REMINDER", f"🎵 Ringtone: '{resolved}' | mode={mode} | snooze={snooze_enabled}")

        # ── TTS: always plays exactly once ────────────────────────────────────
        if mode in ("voice", "both"):
            try:
                from hecos.core.audio.voice import speak
                label = translator.t("ext_reminder_title")
                speak(f"{label}: {title}")
            except Exception as e:
                logger.debug("REMINDER", f"TTS error: {e}")

        # ── Ringtone ──────────────────────────────────────────────────────────
        if mode not in ("ringtone", "both"):
            return  # Voice-only: done

        if not snooze_enabled:
            # Normal mode: play ringtone once
            _play_ringtone_once(resolved)
        else:
            # Snooze mode: loop until user stops
            while not tools.stop_flag:
                _play_ringtone_once(resolved, stop_check=lambda: tools.stop_flag)
                if tools.stop_flag:
                    break
                # Small gap between plays
                for _ in range(10):
                    if tools.stop_flag:
                        break
                    time.sleep(0.1)

        if tools.stop_flag:
            logger.info("REMINDER", "Audio loop interrupted by user.")

    # ── SSE event includes interactive flag so banner renders correctly ─────────
    # Resolve effective interactive value from reminder or system config
    r_interactive = reminder.get("interactive")
    if r_interactive is None:
        try:
            from hecos.app.config import ConfigManager
            _snooze = ConfigManager().config.get("plugins", {}).get("REMINDER", {}).get("reminder_snooze_ui", False)
        except Exception:
            _snooze = False
    else:
        _snooze = bool(r_interactive)

    try:
        from hecos.modules.web_ui.server import get_state_manager
        sm = get_state_manager()
        if sm is not None:
            sm.add_event("reminder_fire", {
                "id":          reminder_id,
                "title":       title,
                "interactive": _snooze,
            })
            logger.info("REMINDER", f"📢 SSE event pushed for [{reminder_id}] interactive={_snooze}")
        else:
            logger.info("REMINDER", "StateManager not available — WebUI push skipped.")
    except Exception as e:
        logger.info("REMINDER", f"WebUI SSE push error: {e}")

    tts_thread = threading.Thread(target=_alert_async, daemon=True, name=f"reminder-alert-{reminder_id}")
    tts_thread.start()

    # ── Mark as fired (one-shot only) ─────────────────────────────────────────
    if not is_repeat:
        try:
            from hecos.plugins.reminder import store
            store.update_status(reminder_id, "fired")
        except Exception as e:
            logger.debug("REMINDER", f"Store update error: {e}")
