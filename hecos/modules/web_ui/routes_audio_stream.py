import os
import sys
import re
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
                    raw_text = recognizer.recognize_google(audio_data, language="it-IT", show_all=False)
                    import re
                    text = re.sub(r'^(slash\s*|barra\s*|/\s*)', '/', (raw_text or "").strip(), flags=re.IGNORECASE)
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
            session_id = data.get("session_id", None)

            from hecos.modules.web_ui.routes_chat_tts import generate_voice_file, set_last_audio_path
            from hecos.config.session_config_manager import merge_session_config

            logger.info(f"[WebUI] TTS Test — engine: {engine or 'active'}, mode: {mode}, text: {text[:60]!r}")
            
            merged_config = merge_session_config(cfg_mgr.config, session_id) if session_id else cfg_mgr.config
            
            ai_cfg = merged_config.get("ai", {})
            session_overrides = {
                "tts_engine": ai_cfg.get("tts_engine"),
                "tts_voice": ai_cfg.get("tts_voice")
            }
            session_overrides.update(ai_cfg.get("voice_overrides", {}))
            
            ui_voice_overrides = merged_config.get("voice", {})
            if ui_voice_overrides:
                if "tts_engine" in ui_voice_overrides and ui_voice_overrides["tts_engine"]:
                    session_overrides["tts_engine"] = ui_voice_overrides["tts_engine"]
                if "tts_voice" in ui_voice_overrides and ui_voice_overrides["tts_voice"]:
                    session_overrides["tts_voice"] = ui_voice_overrides["tts_voice"]
                for k, v in ui_voice_overrides.items():
                    if k.startswith("xtts_") or k.startswith("piper_") or k.startswith("kokoro_") or k.startswith("fish_"):
                        session_overrides[k] = v

            if engine:
                session_overrides["tts_engine"] = engine
                
            voice_config = data.get("voice", {})
            if voice_config:
                session_overrides.update(voice_config)

            job_id = str(uuid.uuid4())

            def _generate_and_maybe_play():
                try:
                    wav_path, wav_id = generate_voice_file(
                        text, 
                        {"session_overrides": session_overrides} if session_overrides else {}, 
                        job_id=job_id
                    )
                    if wav_path:
                        set_last_audio_path(wav_path, wav_id)
                        logger.info(f"[WebUI] TTS Test done — id={wav_id}")
                        if mode == "console":
                            try:
                                # For console mode, generate_voice_file marked it done,
                                # but we can play it here.
                                _play_wav_file(wav_path)
                            except Exception as play_err:
                                logger.error(f"[WebUI] Console playback error: {play_err}")
                    else:
                        logger.error("[WebUI] TTS Test generation returned no path.")
                except Exception as e:
                    import traceback
                    logger.error(f"[WebUI] TTS Test worker error: {e}\n{traceback.format_exc()}")

            threading.Thread(target=_generate_and_maybe_play, daemon=True).start()
            return jsonify({"ok": True, "job_id": job_id})

        except Exception as exc:
            import traceback
            logger.error(f"[WebUI] test_audio error: {exc}\n{traceback.format_exc()}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route("/api/audio/voice-clones", methods=["GET"])
    def list_voice_clones():
        """List all WAV files in the assets/voice_clones directory, with companion transcripts."""
        try:
            clones_dir = os.path.join(root_dir, "hecos", "assets", "voice_clones")
            os.makedirs(clones_dir, exist_ok=True)
            files = []
            for fname in sorted(os.listdir(clones_dir)):
                if fname.lower().endswith(".wav"):
                    full_path = os.path.join(clones_dir, fname)
                    txt_path = os.path.splitext(full_path)[0] + ".txt"
                    transcript = ""
                    if os.path.exists(txt_path):
                        try:
                            with open(txt_path, "r", encoding="utf-8") as tf:
                                transcript = tf.read().strip()
                        except Exception:
                            pass
                    files.append({
                        "name": os.path.splitext(fname)[0],
                        "filename": fname,
                        "path": full_path,
                        "transcript": transcript
                    })
            return jsonify({"ok": True, "files": files, "dir": clones_dir})
        except Exception as exc:
            logger.error(f"[WebUI] list_voice_clones error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route("/api/audio/voice-clones/transcript", methods=["POST"])
    def update_voice_clone_transcript():
        """Update or create a companion .txt transcript for a voice clone."""
        try:
            data = request.get_json(force=True) or {}
            filename = data.get("filename", "").strip()
            transcript = data.get("transcript", "").strip()
            if not filename:
                return jsonify({"ok": False, "error": "Missing filename"}), 400
            clones_dir = os.path.join(root_dir, "hecos", "assets", "voice_clones")
            base = os.path.splitext(os.path.basename(filename))[0]
            txt_path = os.path.join(clones_dir, f"{base}.txt")
            with open(txt_path, "w", encoding="utf-8") as tf:
                tf.write(transcript)
            logger.info(f"[WebUI] Voice clone transcript saved for {base}: {len(transcript)} chars")
            return jsonify({"ok": True, "filename": filename, "transcript": transcript})
        except Exception as exc:
            logger.error(f"[WebUI] update_voice_clone_transcript error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

def _normalize_to_pcm_wav(file_path: str):
    """Ensures audio file is a valid 16-bit PCM WAV. If compressed (e.g. WebM/Opus from browser), converts it using ffmpeg."""
    try:
        import soundfile as sf
        sf.read(file_path)
    except Exception:
        tmp_dest = file_path + ".tmp"
        try:
            os.replace(file_path, tmp_dest)
            subprocess.run(
                ["ffmpeg", "-y", "-i", tmp_dest, "-ar", "24000", "-ac", "1", "-c:a", "pcm_s16le", file_path],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True
            )
        except Exception:
            if not os.path.exists(file_path) and os.path.exists(tmp_dest):
                os.replace(tmp_dest, file_path)
        finally:
            if os.path.exists(tmp_dest):
                try:
                    os.remove(tmp_dest)
                except Exception:
                    pass

    @app.route("/api/audio/voice-clones/upload", methods=["POST"])
    def upload_voice_clone():
        """Upload a WAV file into assets/voice_clones/."""
        try:
            if "file" not in request.files:
                return jsonify({"ok": False, "error": "No file provided"}), 400
            f = request.files["file"]
            if not f.filename.lower().endswith(".wav"):
                return jsonify({"ok": False, "error": "Only WAV files are accepted"}), 400
            clones_dir = os.path.join(root_dir, "hecos", "assets", "voice_clones")
            os.makedirs(clones_dir, exist_ok=True)
            safe_name = os.path.basename(f.filename)
            dest = os.path.join(clones_dir, safe_name)
            f.save(dest)
            _normalize_to_pcm_wav(dest)
            logger.info(f"[WebUI] Voice clone uploaded: {dest}")
            return jsonify({"ok": True, "path": dest, "filename": safe_name})
        except Exception as exc:
            logger.error(f"[WebUI] upload_voice_clone error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route("/api/audio/voice-clones/save-recorded", methods=["POST"])
    def save_recorded_voice_clone():
        """Saves a recorded WAV file from browser with custom timbre name and transcript."""
        try:
            if "file" not in request.files:
                return jsonify({"ok": False, "error": "No audio file provided"}), 400
            f = request.files["file"]
            name = (request.form.get("name") or "").strip()
            transcript = (request.form.get("transcript") or "").strip()
            
            if not name:
                name = f"voice_clone_{int(time.time())}"
            # sanitize name
            safe_base = re.sub(r'[^a-zA-Z0-9_\- ]', '', name).strip().replace(' ', '_').lower()
            if not safe_base:
                safe_base = f"timbre_{int(time.time())}"

            clones_dir = os.path.join(root_dir, "hecos", "assets", "voice_clones")
            os.makedirs(clones_dir, exist_ok=True)
            wav_name = f"{safe_base}.wav"
            dest_wav = os.path.join(clones_dir, wav_name)
            dest_txt = os.path.join(clones_dir, f"{safe_base}.txt")

            f.save(dest_wav)
            _normalize_to_pcm_wav(dest_wav)
            if transcript:
                with open(dest_txt, "w", encoding="utf-8") as tf:
                    tf.write(transcript)

            logger.info(f"[WebUI] Saved recorded timbre '{safe_base}': {os.path.getsize(dest_wav)} bytes, transcript={len(transcript)} chars")
            return jsonify({
                "ok": True,
                "path": dest_wav,
                "filename": wav_name,
                "name": safe_base,
                "transcript": transcript
            })
        except Exception as exc:
            logger.error(f"[WebUI] save_recorded_voice_clone error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route("/api/audio/voice-clones/delete", methods=["POST"])
    def delete_voice_clone():
        """Deletes a voice clone WAV and its companion .txt file."""
        try:
            data = request.get_json(force=True) or {}
            filename = (data.get("filename") or "").strip()
            if not filename:
                return jsonify({"ok": False, "error": "Missing filename"}), 400

            clones_dir = os.path.join(root_dir, "hecos", "assets", "voice_clones")
            base = os.path.splitext(os.path.basename(filename))[0]
            wav_path = os.path.join(clones_dir, f"{base}.wav")
            txt_path = os.path.join(clones_dir, f"{base}.txt")

            deleted = []
            if os.path.exists(wav_path):
                os.remove(wav_path)
                deleted.append(f"{base}.wav")
            if os.path.exists(txt_path):
                os.remove(txt_path)
                deleted.append(f"{base}.txt")

            logger.info(f"[WebUI] Deleted voice clone timbre files: {deleted}")
            return jsonify({"ok": True, "deleted": deleted})
        except Exception as exc:
            logger.error(f"[WebUI] delete_voice_clone error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500
