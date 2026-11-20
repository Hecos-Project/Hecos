"""
Hecos Web UI - Audio Controls Routes
Endpoints for speaking states, microphone listening toggle, TTS toggle, PTT, playback stop, and audio history.
"""

import os
import glob
import threading
from flask import request, jsonify


def register_audio_controls_routes(app, cfg_mgr, root_dir, logger, get_sm=None):
    """Registers audio playback, speaking status, toggles and history endpoints."""
    def _sm():
        return get_sm() if callable(get_sm) else get_sm

    _speaking_timer = None

    @app.route("/api/audio/speaking/start", methods=["POST"])
    def speaking_start():
        nonlocal _speaking_timer
        sm = _sm()
        if sm:
            sm.system_speaking = True
            logger.debug("[WebUI] Audio speaking started on browser, pausing system mic.")
            if _speaking_timer:
                try:
                    _speaking_timer.cancel()
                except Exception:
                    pass

            def _auto_reset():
                if sm:
                    sm.system_speaking = False
                    logger.debug("[WebUI] Auto-reset system_speaking to False after safety timeout.")

            _speaking_timer = threading.Timer(90.0, _auto_reset)
            _speaking_timer.daemon = True
            _speaking_timer.start()
        return jsonify({"ok": True})

    @app.route("/api/audio/speaking/stop", methods=["POST"])
    def speaking_stop():
        nonlocal _speaking_timer
        if _speaking_timer:
            try:
                _speaking_timer.cancel()
            except Exception:
                pass
            _speaking_timer = None
        sm = _sm()
        if sm:
            sm.system_speaking = False
            logger.debug("[WebUI] Audio speaking stopped on browser, resuming system mic.")
        return jsonify({"ok": True})

    @app.route("/api/audio/toggle/mic", methods=["POST"])
    def toggle_mic():
        """Toggle listening_status (MIC continuous listening).
        If MIC is turned OFF, also force PTT off to prevent a silent PTT state."""
        try:
            from hecos.core.audio.device_manager import get_audio_config, _save_audio_config
            acfg = get_audio_config()
            new_mic = not acfg.get("listening_status", True)

            sm = _sm()
            if sm is not None:
                sm.listening_status = new_mic

            acfg["listening_status"] = new_mic

            # Auto-disable PTT when MIC is turned OFF
            forced_ptt_off = False
            if not new_mic and acfg.get("push_to_talk", False):
                acfg["push_to_talk"] = False
                forced_ptt_off = True
                if sm is not None:
                    sm.push_to_talk = False
                logger.info("[WebUI] PTT auto-disabled because MIC was turned OFF.")

            if _save_audio_config(acfg):
                logger.info(f"[WebUI] MIC toggled to {new_mic} and saved.")
            else:
                logger.error("[WebUI] Failed to save MIC toggle.")

            try:
                from hecos.core.audio import ptt_bus
                ptt_bus.update_cache()
            except Exception:
                pass

            try:
                from hecos.core.processing import processore
                processore.configure(cfg_mgr.config)
            except Exception:
                pass

            return jsonify({
                "ok": True,
                "listening_status": new_mic,
                "push_to_talk": acfg.get("push_to_talk", False),
                "ptt_forced_off": forced_ptt_off
            })
        except Exception as exc:
            logger.error(f"[WebUI] toggle_mic error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route("/api/audio/toggle/tts", methods=["POST"])
    def toggle_tts():
        """Toggle voice_status - mirrors F5 on the console."""
        try:
            from hecos.core.audio.device_manager import get_audio_config, _save_audio_config
            acfg = get_audio_config()
            new_val = not acfg.get("voice_status", True)

            sm = _sm()
            if sm is not None:
                sm.voice_status = new_val

            acfg["voice_status"] = new_val
            if _save_audio_config(acfg):
                logger.info(f"[WebUI] TTS toggled to {new_val} and saved.")
            else:
                logger.error("[WebUI] Failed to save TTS toggle.")
            try:
                from hecos.core.processing import processore
                processore.configure(cfg_mgr.config)
            except Exception:
                pass
            return jsonify({"ok": True, "voice_status": new_val})
        except Exception as exc:
            logger.error(f"[WebUI] toggle_tts error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route("/api/audio/toggle/ptt", methods=["POST"])
    def toggle_ptt():
        """Toggle push_to_talk flag.
        PTT can only be ENABLED if listening_status (continuous MIC) is also ON."""
        try:
            sm = _sm()
            from hecos.core.audio.device_manager import get_audio_config, _save_audio_config
            acfg = get_audio_config()
            current_ptt = acfg.get("push_to_talk", False)
            new_val = not current_ptt

            # Guard: PTT cannot be enabled if MIC is OFF
            if new_val and not acfg.get("listening_status", True):
                return jsonify({
                    "ok": False,
                    "error": "Enable MIC (continuous listening) before activating PTT.",
                    "push_to_talk": False
                }), 400

            acfg["push_to_talk"] = new_val
            if _save_audio_config(acfg):
                logger.info(f"[WebUI] PTT toggled to {new_val} and saved.")
            else:
                logger.error("[WebUI] Failed to save PTT toggle.")
            if sm is not None:
                sm.push_to_talk = new_val
            try:
                from hecos.core.audio import ptt_bus
                ptt_bus.update_cache()
            except Exception:
                pass
            return jsonify({"ok": True, "push_to_talk": new_val})
        except Exception as exc:
            logger.error(f"[WebUI] toggle_ptt error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route("/api/audio/stop", methods=["POST"])
    def audio_stop():
        """Stop any active TTS playback."""
        try:
            from hecos.core.audio.tts_manager import TTSManager
            TTSManager.stop()
            return jsonify({"ok": True})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/audio/history/info", methods=["GET"])
    def audio_history_info():
        """Returns count and total size of WAV files in media/audio/history/."""
        try:
            from hecos.modules.web_ui.routes_chat_tts import HISTORY_DIR
            files = glob.glob(os.path.join(HISTORY_DIR, "*.wav"))
            total_bytes = sum(os.path.getsize(f) for f in files if os.path.exists(f))
            size_mb = round(total_bytes / (1024 * 1024), 2)
            return jsonify({"ok": True, "count": len(files), "size_mb": size_mb})
        except Exception as e:
            logger.error(f"[WebUI] audio_history_info error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/audio/history/clear", methods=["POST"])
    def audio_history_clear():
        """Deletes all WAV files in media/audio/history/."""
        try:
            from hecos.modules.web_ui.routes_chat_tts import HISTORY_DIR
            files = glob.glob(os.path.join(HISTORY_DIR, "*.wav"))
            deleted = 0
            for f in files:
                try:
                    os.remove(f)
                    deleted += 1
                except Exception:
                    pass
            logger.info(f"[WebUI] audio_history_clear: deleted {deleted} file(s).")
            return jsonify({"ok": True, "deleted": deleted})
        except Exception as e:
            logger.error(f"[WebUI] audio_history_clear error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

