import os
import json
import threading
import time
import uuid
from flask import request, jsonify, Response, stream_with_context

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
            # Monkey-patch speech_recognition to use soundfile for FLAC conversion.
            # This prevents it from falling back to the legacy flac-win32.exe (blocked on Win 11).
            try:
                import soundfile as sf
                import io
                def _custom_get_flac_data(self, convert_rate=None, convert_width=None):
                    wav_data = self.get_wav_data(convert_rate, convert_width)
                    wav_io = io.BytesIO(wav_data)
                    data, samplerate = sf.read(wav_io)
                    flac_io = io.BytesIO()
                    sf.write(flac_io, data, samplerate, format='FLAC')
                    return flac_io.getvalue()
                sr.AudioData.get_flac_data = _custom_get_flac_data
            except ImportError:
                pass

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

    @app.route("/api/audio/test/progress/<job_id>", methods=["GET"])
    def tts_progress(job_id):
        from hecos.modules.web_ui.routes_chat_tts import get_tts_progress
        
        def generate():
            while True:
                prog = get_tts_progress(job_id)
                if not prog:
                    yield f"data: {json.dumps({'status': 'not_found'})}\n\n"
                    break
                    
                yield f"data: {json.dumps(prog)}\n\n"
                
                if prog["status"] in ["done", "error"]:
                    break
                time.sleep(0.2)
                
        return Response(stream_with_context(generate()), mimetype="text/event-stream")

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
        """Test TTS with a custom text using the active engine (Piper, Kokoro, XTTS2).
        mode='web':     generates WAV async, returns job_id for SSE progress polling.
        mode='console': speaks server-side (blocking).
        """
        try:
            data = request.get_json(force=True) or {}
            text = data.get("text", "Test di Hecos, sistema vocale operativo.").strip()
            mode = data.get("mode", "web")

            from hecos.core.audio.tts_manager import TTSManager
            from hecos.modules.web_ui.routes_chat_tts import generate_voice_file, set_last_audio_path

            logger.info(f"[WebUI] TTS Test — engine: active, mode: {mode}, text: {text[:60]!r}")

            if mode == "console":
                # Speak on server speakers (non-blocking for Flask, runs in thread)
                def _speak():
                    try:
                        TTSManager.speak(text)
                    except Exception as e:
                        logger.error(f"[WebUI] Console TTS speak error: {e}")
                threading.Thread(target=_speak, daemon=True).start()
                return jsonify({"ok": True, "msg": "Playing on server speakers..."})

            else:
                # Web mode: async generation + SSE progress
                job_id = str(uuid.uuid4())

                def _generate_web():
                    try:
                        wav_path, wav_id = generate_voice_file(text, {}, job_id=job_id)
                        if wav_path:
                            set_last_audio_path(wav_path, wav_id)
                            logger.info(f"[WebUI] TTS Test done — id={wav_id}")
                        else:
                            logger.error("[WebUI] TTS Test generation returned no path.")
                    except Exception as e:
                        import traceback
                        logger.error(f"[WebUI] TTS Test _generate_web error: {e}\n{traceback.format_exc()}")

                threading.Thread(target=_generate_web, daemon=True).start()
                return jsonify({"ok": True, "job_id": job_id})

        except Exception as exc:
            import traceback
            logger.error(f"[WebUI] test_audio error: {exc}\n{traceback.format_exc()}")
            return jsonify({"ok": False, "error": str(exc)}), 500
