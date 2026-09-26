import os
import sys
import json
import threading
import time
import uuid
import subprocess
from flask import request, jsonify, Response, stream_with_context

def _play_wav_file(file_path):
    """Riproduce un file WAV in modo multipiattaforma senza librerie esterne."""
    if sys.platform == "win32":
        import winsound
        winsound.PlaySound(file_path, winsound.SND_FILENAME)
    elif sys.platform == "darwin":
        subprocess.run(["afplay", file_path], check=False)
    else:
        # Linux / Unix: tenta i principali riproduttori audio CLI in ordine di disponibilità
        for cmd in ["paplay", "aplay", "ffplay", "cvlc"]:
            if subprocess.run(["which", cmd], capture_output=True).returncode == 0:
                if cmd == "ffplay":
                    subprocess.run([cmd, "-nodisp", "-autoexit", "-loglevel", "quiet", file_path], check=False)
                elif cmd == "cvlc":
                    subprocess.run([cmd, "--play-and-exit", file_path], check=False)
                else:
                    subprocess.run([cmd, file_path], check=False)
                break

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

            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_in:
                audio_file.save(tmp_in.name)
                tmp_in_path = tmp_in.name

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
            engine = data.get("engine", None)

            from hecos.modules.web_ui.routes_chat_tts import generate_voice_file, set_last_audio_path, _run_xtts2_bypass

            logger.info(f"[WebUI] TTS Test — engine: {engine or 'active'}, mode: {mode}, text: {text[:60]!r}")
            
            session_overrides = {"tts_engine": engine} if engine else {}

            if mode == "console":
                def _speak():
                    try:
                        if engine in ['xtts2', 'xtts']:
                            import tempfile
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                                tmp_path = tmp.name
                            if _run_xtts2_bypass(text, tmp_path, {"session_overrides": session_overrides}):
                                try:
                                    _play_wav_file(tmp_path)
                                except Exception as play_err:
                                    logger.error(f"[WebUI] Console playback error: {play_err}")
                                finally:
                                    if os.path.exists(tmp_path):
                                        os.remove(tmp_path)
                            else:
                                logger.error("[WebUI] Console XTTS2 bypass failed.")
                        else:
                            from hecos.core.audio.tts_manager import TTSManager
                            TTSManager.speak(text, session_overrides=session_overrides)
                    except Exception as e:
                        logger.error(f"[WebUI] Console TTS speak error: {e}")
                threading.Thread(target=_speak, daemon=True).start()
                return jsonify({"ok": True, "msg": "Playing on server speakers..."})

            else:
                job_id = str(uuid.uuid4())

                def _generate_web():
                    try:
                        wav_path, wav_id = generate_voice_file(
                            text, 
                            {"session_overrides": session_overrides} if session_overrides else {}, 
                            job_id=job_id
                        )
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

    @app.route("/api/audio/voice-clones", methods=["GET"])
    def list_voice_clones():
        """List all WAV files in the assets/voice_clones directory."""
        try:
            clones_dir = os.path.join(root_dir, "assets", "voice_clones")
            os.makedirs(clones_dir, exist_ok=True)
            files = []
            for fname in sorted(os.listdir(clones_dir)):
                if fname.lower().endswith(".wav"):
                    full_path = os.path.join(clones_dir, fname)
                    files.append({
                        "name": os.path.splitext(fname)[0],
                        "filename": fname,
                        "path": full_path
                    })
            return jsonify({"ok": True, "files": files, "dir": clones_dir})
        except Exception as exc:
            logger.error(f"[WebUI] list_voice_clones error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route("/api/audio/voice-clones/upload", methods=["POST"])
    def upload_voice_clone():
        """Upload a WAV file into assets/voice_clones/."""
        try:
            if "file" not in request.files:
                return jsonify({"ok": False, "error": "No file provided"}), 400
            f = request.files["file"]
            if not f.filename.lower().endswith(".wav"):
                return jsonify({"ok": False, "error": "Only WAV files are accepted"}), 400
            clones_dir = os.path.join(root_dir, "assets", "voice_clones")
            os.makedirs(clones_dir, exist_ok=True)
            safe_name = os.path.basename(f.filename)
            dest = os.path.join(clones_dir, safe_name)
            f.save(dest)
            logger.info(f"[WebUI] Voice clone uploaded: {dest}")
            return jsonify({"ok": True, "path": dest, "filename": safe_name})
        except Exception as exc:
            logger.error(f"[WebUI] upload_voice_clone error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500