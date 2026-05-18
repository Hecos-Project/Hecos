import os
import json
import threading
import time
from flask import request, jsonify

def init_audio_stream_routes(app, cfg_mgr, root_dir, logger, get_sm=None):
    def _sm():
        return get_sm() if callable(get_sm) else get_sm

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
            from hecos.core.audio.voice import stop_voice
            stop_voice()
            
            sm = _sm()
            if sm: sm.system_speaking = False
            
            try:
                from hecos.modules.web_ui.routes_chat import stop_voice_generation
                stop_voice_generation()
            except Exception as e:
                logger.debug(f"[WebUI] Could not stop web generation: {e}")
            logger.info("[WebUI] TTS stopped via API (ESC).")
            return jsonify({"ok": True})
        except Exception as exc:
            logger.error(f"[WebUI] stop_audio error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route("/api/audio/test", methods=["POST"])
    def test_audio():
        """Test Piper TTS with a custom text.
        mode='web': generates WAV and returns a URL for browser playback.
        mode='console': generates WAV and plays it server-side.
        """
        try:
            data = request.get_json(force=True) or {}
            text = data.get("text", "Test di Hecos, sistema vocale operativo.").strip()
            mode = data.get("mode", "web")

            from hecos.core.audio.device_manager import get_audio_config
            voice_cfg = get_audio_config()

            # Dynamic root resolution
            this_file = os.path.abspath(__file__)
            hecos_root = os.path.normpath(os.path.join(os.path.dirname(this_file), "..", "..", ".."))
            default_piper_dir = os.path.join(hecos_root, "bin", "piper")
            piper_exe_name = "piper.exe" if os.name == "nt" else "piper"

            piper_path = voice_cfg.get("piper_path") or os.path.join(default_piper_dir, piper_exe_name)
            onnx_model = voice_cfg.get("onnx_model") or ""

            if onnx_model and not os.path.isabs(onnx_model):
                onnx_model = os.path.join(default_piper_dir, onnx_model)

            logger.info(f"[WebUI] TTS Test — piper: {piper_path}, model: {onnx_model}")

            if not os.path.exists(piper_path):
                return jsonify({
                    "ok": False,
                    "error": f"Piper executable not found at: {piper_path}. Please use the Auto button or check the path."
                }), 400

            if not onnx_model or not os.path.exists(onnx_model):
                import glob as _glob
                found_onnx = _glob.glob(os.path.join(default_piper_dir, "*.onnx"))
                if found_onnx:
                    onnx_model = found_onnx[0]
                    logger.info(f"[WebUI] TTS Test — using fallback ONNX model: {onnx_model}")
                else:
                    return jsonify({
                        "ok": False,
                        "error": f"ONNX model not found at: {onnx_model}. Please select a valid voice in configuration."
                    }), 400

            voice_cfg["piper_path"] = piper_path
            voice_cfg["onnx_model"] = onnx_model

            from hecos.modules.web_ui.routes_chat import generate_voice_file, set_last_audio_path
            wav_path = generate_voice_file(text, voice_cfg)

            if not wav_path:
                return jsonify({
                    "ok": False,
                    "error": "Piper synthesis failed. Check Hecos logs for details."
                }), 500

            if mode == "web":
                set_last_audio_path(wav_path)
                return jsonify({"ok": True, "url": "/api/audio"})
            else:
                def _play_server_side():
                    try:
                        from hecos.core.audio.voice import _play_wav
                        _play_wav(wav_path)
                    except Exception as play_e:
                        logger.error(f"[WebUI] Console TTS play error: {play_e}")

                threading.Thread(target=_play_server_side, daemon=True).start()
                return jsonify({"ok": True, "msg": "Playing on server speakers..."})

        except Exception as exc:
            import traceback
            logger.error(f"[WebUI] test_audio error: {exc}\n{traceback.format_exc()}")
            return jsonify({"ok": False, "error": str(exc)}), 500
