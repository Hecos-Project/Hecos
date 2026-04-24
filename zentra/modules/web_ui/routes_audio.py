import os
import json
import threading
import time
from flask import request, jsonify

def init_audio_routes(app, cfg_mgr, root_dir, logger, get_sm=None):
    def _sm():
        return get_sm() if callable(get_sm) else get_sm

    # ── Audio Control API ─────────────────────────────────────────────────────

    @app.route("/api/audio/transcribe", methods=["POST"])
    def transcribe_audio():
        """Accepts a WebRTC audio blob from the browser, converts to WAV, and transcribes."""
        try:
            if "audio_file" not in request.files:
                return jsonify({"ok": False, "error": "No audio_file in request"}), 400
                
            audio_file = request.files["audio_file"]
            if not audio_file.filename:
                return jsonify({"ok": False, "error": "No selected file"}), 400

            import tempfile
            import speech_recognition as sr

            # Since the frontend now converts to WAV directly via AudioContext,
            # we can just save it and pass it to speech_recognition natively, skipping ffmpeg.
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_in:
                audio_file.save(tmp_in.name)
                tmp_in_path = tmp_in.name

            # Transcribe via speech_recognition
            text = ""
            try:
                recognizer = sr.Recognizer()
                with sr.AudioFile(tmp_in_path) as source:
                    audio_data = recognizer.record(source)
                    logger.info("[WebUI] Transcribing WebRTC audio via Google STT...")
                    text = recognizer.recognize_google(audio_data, language="it-IT", show_all=False)
            except sr.UnknownValueError:
                logger.warning("[WebUI] WebRTC audio transcription could not understand audio.")
            except Exception as e:
                logger.error(f"[WebUI] WebRTC transcription error: {e}")
            finally:
                # Cleanup temp file
                if os.path.exists(tmp_in_path):
                    os.remove(tmp_in_path)

            return jsonify({"ok": True, "text": text})

        except Exception as exc:
            logger.error(f"[WebUI] transcribe_audio error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500


    @app.route("/api/audio/stop", methods=["POST"])
    def stop_audio():
        """Stop server-side TTS playback and generation."""
        try:
            from zentra.core.audio.voice import stop_voice
            stop_voice()
            
            sm = _sm()
            if sm: sm.system_speaking = False
            
            try:
                from modules.web_ui.routes_chat import stop_voice_generation
                stop_voice_generation()
            except Exception as e:
                logger.debug(f"[WebUI] Could not stop web generation: {e}")
            logger.info("[WebUI] TTS stopped via API (ESC).")
            return jsonify({"ok": True})
        except Exception as exc:
            logger.error(f"[WebUI] stop_audio error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route("/api/audio/speaking/start", methods=["POST"])
    def speaking_start():
        sm = _sm()
        if sm:
            sm.system_speaking = True
            logger.debug("[WebUI] Audio speaking started on browser, pausing system mic.")
        return jsonify({"ok": True})

    @app.route("/api/audio/speaking/stop", methods=["POST"])
    def speaking_stop():
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
            from zentra.core.audio.device_manager import get_audio_config, _save_audio_config
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
                from zentra.core.processing import processore
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
        """Toggle voice_status — mirrors F5 on the console."""
        try:
            from zentra.core.audio.device_manager import get_audio_config, _save_audio_config
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
                from zentra.core.processing import processore
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
        PTT can only be ENABLED if listening_status (continuous MIC) is also ON.
        PTT is a sub-mode of mic input, not an independent feature."""
        try:
            sm = _sm()
            from zentra.core.audio.device_manager import get_audio_config, _save_audio_config
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
            return jsonify({"ok": True, "push_to_talk": new_val})
        except Exception as exc:
            logger.error(f"[WebUI] toggle_ptt error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    # ── Audio Controls API ───────────────────────────────────────────

    @app.route("/api/audio/config", methods=["GET", "POST"])
    def manage_audio_config():
        """Gets or updates advanced audio settings in config_audio.json."""
        from zentra.core.audio.device_manager import get_audio_config, _save_audio_config

        if request.method == "GET":
            try:
                return jsonify({"ok": True, "config": get_audio_config()})
            except Exception as exc:
                return jsonify({"ok": False, "error": str(exc)}), 500

        if request.method == "POST":
            try:
                data = request.get_json(force=True) or {}
                cfg = get_audio_config()
                for k in ["voice_status", "listening_status", "piper_path", "onnx_model",
                          "speed", "noise_scale", "noise_w", "sentence_silence",
                          "energy_threshold", "silence_timeout", "phrase_limit"]:
                    if k in data:
                        cfg[k] = data[k]

                _save_audio_config(cfg)

                # Sync with running StateManager
                sm = _sm()
                if sm:
                    if "listening_status" in data:
                        sm.listening_status = data["listening_status"]
                    if "voice_status" in data:
                        sm.voice_status = data["voice_status"]
                    if "push_to_talk" in data:
                        sm.push_to_talk = data["push_to_talk"]

                # If voice capabilities changed, we must update the processor
                if any(k in data for k in ["voice_status", "listening_status"]):
                    try:
                        from zentra.core.processing import processore
                        processore.configure(cfg_mgr.config)
                    except Exception:
                        pass

                return jsonify({"ok": True})
            except Exception as exc:
                logger.error(f"[WebUI] manage_audio_config POST error: {exc}")
                return jsonify({"ok": False, "error": str(exc)}), 500
