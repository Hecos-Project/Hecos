import os
import json
import threading
import time
from flask import request, jsonify, render_template

def init_routes(app, cfg_mgr, root_dir, logger, get_sm=None):
    """
    get_sm: callable that returns the current StateManager (or None).
    Using a getter ensures late-binding after the server starts.
    """
    def _sm():
        return get_sm() if callable(get_sm) else get_sm


    @app.route("/zentra/config/ui")
    def config_ui():
        try:
            return render_template("index.html")
        except Exception as e:
            return f"<h1>Errore: index.html non trovato</h1><p>{str(e)}</p>", 500

    @app.route("/zentra/config", methods=["GET"])
    def get_config():
        cfg = cfg_mgr.reload()
        return jsonify(cfg)

    @app.route("/api/models/refresh", methods=["POST"])
    def refresh_models():
        from app.model_manager import ModelManager
        mm = ModelManager(cfg_mgr)
        mm.get_available_models() # This updates the cache in config
        return jsonify({"ok": True})

    @app.route("/zentra/options", methods=["GET"])
    def get_options():
        import glob
        cfg = cfg_mgr.reload()
        
        piper_path_dir = r"C:\piper"
        try:
            onnx_files = [os.path.basename(f) for f in glob.glob(os.path.join(piper_path_dir, "*.onnx"))]
            if not onnx_files: onnx_files = ["en_US-lessac-medium.onnx"]
        except:
            onnx_files = ["en_US-lessac-medium.onnx"]
            
        from app.model_manager import ModelManager
        mm = ModelManager(cfg_mgr)
        categorized = mm.get_available_models()
        
        ollama_models = categorized.get("Ollama (Local)", [])
        personalita   = list(cfg.get("ai", {}).get("available_personalities", {}).values())
        
        # Flatten cloud models for the simple dropdown
        cloud_models_flat = []
        cloud_by_provider = {}
        for cat, models in categorized.items():
            if "Cloud" in cat:
                cloud_models_flat.extend(models)
                provider = cat.replace("Cloud (", "").replace(")", "").lower()
                cloud_by_provider[provider] = models

        return jsonify({
            "piper_voices": onnx_files,
            "piper_dir":    piper_path_dir,
            "ollama_models": ollama_models,
            "personalities": personalita,
            "cloud_models":  cloud_by_provider,
            "all_cloud":     cloud_models_flat
        })

    @app.route("/zentra/config", methods=["POST"])
    def post_config():
        try:
            incoming = request.get_json(force=True)
            if not isinstance(incoming, dict):
                return jsonify({"ok": False, "error": "Invalid payload"}), 400
            cfg_mgr.config = incoming
            if cfg_mgr.save():
                # Dynamically update the global translator language without reboot
                from core.i18n.translator import get_translator
                get_translator().set_language(incoming.get("language", "en"))
                # Keep state_manager in sync with saved audio_mode
                sm = _sm()
                if sm is not None:
                    sm.audio_mode = incoming.get("audio_mode", "auto")
                    sm.voice_status = incoming.get("voice", {}).get("voice_status", sm.voice_status)
                    sm.listening_status = incoming.get("listening", {}).get("listening_status", sm.listening_status)
                return jsonify({"ok": True})
            return jsonify({"ok": False, "error": "Save failed"}), 500
        except Exception as exc:
            logger.error(f"[WebUI] POST /config error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route("/zentra/status", methods=["GET"])
    def get_status():
        try:
            cfg     = cfg_mgr.config
            backend = cfg.get("backend", {}).get("type", "?")
            if   backend == "cloud":  model = cfg.get("backend", {}).get("cloud",  {}).get("model", "?")
            elif backend == "ollama": model = cfg.get("backend", {}).get("ollama", {}).get("model", "?")
            elif backend == "kobold": model = cfg.get("backend", {}).get("kobold", {}).get("model", "?")
            else: model = "?"

            br      = cfg.get("bridge", {})
            voice   = cfg.get("voice", {})
            listen  = cfg.get("listening", {})

            flags = [k for k, v in [
                ("proc",        br.get("use_processor")),
                ("think-strip", br.get("remove_think_tags")),
                ("tools",       br.get("enable_tools")),
            ] if v]

            # Read live state from state_manager if available, else fall back to config
            sm = _sm()
            if sm is not None:
                mic_on     = sm.listening_status
                tts_on     = sm.voice_status
                audio_mode = sm.audio_mode
            else:
                from core.audio.device_manager import get_audio_config
                acfg = get_audio_config()
                mic_on     = acfg.get("listening_status", False)
                tts_on     = acfg.get("voice_status", False)
                audio_mode = cfg.get("audio_mode", "auto")

            mic_status = "ON" if mic_on else "OFF"
            tts_status = "ON" if tts_on else "OFF"
            
            from core.audio.device_manager import get_audio_config
            acfg = get_audio_config()
            ptt_on     = acfg.get("push_to_talk", False)
            ptt_status = "ON" if ptt_on else "OFF"

            from datetime import datetime
            config_path = os.path.join(root_dir, "config.json")
            mtime = os.path.getmtime(config_path) if os.path.exists(config_path) else 0
            ts    = datetime.fromtimestamp(mtime).strftime("%H:%M:%S") if mtime else "?"

            # Granular routing
            stt_s = sm.stt_source if sm else acfg.get("stt_source", "system")
            tts_d = sm.tts_destination if sm else acfg.get("tts_destination", "web")

            return jsonify({
                "backend":    backend.upper(),
                "model":      model,
                "bridge":     ", ".join(flags) if flags else "default",
                "mic":        mic_status,
                "tts":        tts_status,
                "ptt":        ptt_status,
                "audio_config": {
                    "stt_source": stt_s,
                    "tts_destination": tts_d
                },
                "config":     f"last save {ts}",
            })
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    # ── Memory Control API ─────────────────────────────────────────────────────

    @app.route("/api/memory/clear", methods=["POST"])
    def memory_clear():
        """Wipes the episodic history from the DB."""
        try:
            from memory.brain_interface import clear_history
            cleared = clear_history()
            if cleared:
                logger.info("[WebUI] Chat history cleared via API.")
                return jsonify({"ok": True, "message": "History cleared."})
            return jsonify({"ok": False, "error": "Failed to clear."}), 500
        except Exception as exc:
            logger.error(f"[WebUI] memory_clear error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route("/api/memory/status", methods=["GET"])
    def memory_status():
        """Returns memory row count and config."""
        try:
            import sqlite3, os
            db_path = os.path.join("memory", "chat_history.db")
            count = 0
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                count = conn.execute("SELECT COUNT(*) FROM history").fetchone()[0]
                conn.close()
            cog = cfg_mgr.config.get("cognition", {})
            return jsonify({"ok": True, "total_messages": count, "cognition": cog})
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 500

    # ── Audio Control API ─────────────────────────────────────────────────────

    @app.route("/api/audio/stop", methods=["POST"])
    def stop_audio():
        """Stop server-side TTS playback and generation."""
        try:
            # Stop playback and system-routing generation
            from core.audio.voice import stop_voice
            stop_voice()
            
            # Stop web-routing generation
            try:
                from plugins.web_ui.routes_chat import stop_voice_generation
                stop_voice_generation()
            except Exception as e:
                logger.debug(f"[WebUI] Could not stop web generation: {e}")

            logger.info("[WebUI] TTS stopped via API (ESC).")
            return jsonify({"ok": True})
        except Exception as exc:
            logger.error(f"[WebUI] stop_audio error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route("/api/audio/toggle/mic", methods=["POST"])
    def toggle_mic():
        """Toggle listening_status — mirrors F4 on the console."""
        try:
            sm = _sm()
            if sm is None:
                return jsonify({"ok": False, "error": "State manager not available"}), 503
            new_val = not sm.listening_status
            sm.listening_status = new_val
            
            from core.audio.device_manager import get_audio_config, _save_audio_config
            acfg = get_audio_config()
            acfg["listening_status"] = new_val
            if _save_audio_config(acfg):
                logger.info(f"[WebUI] MIC toggled to {new_val} and saved.")
            else:
                logger.error("[WebUI] Failed to save MIC toggle.")
            # Keep processore in sync
            try:
                from core.processing import processore
                processore.configure(cfg_mgr.config)
            except Exception:
                pass
            return jsonify({"ok": True, "listening_status": new_val})
        except Exception as exc:
            logger.error(f"[WebUI] toggle_mic error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route("/api/audio/toggle/tts", methods=["POST"])
    def toggle_tts():
        """Toggle voice_status — mirrors F5 on the console."""
        try:
            sm = _sm()
            if sm is None:
                return jsonify({"ok": False, "error": "State manager not available"}), 503
            new_val = not sm.voice_status
            sm.voice_status = new_val
            
            from core.audio.device_manager import get_audio_config, _save_audio_config
            acfg = get_audio_config()
            acfg["voice_status"] = new_val
            if _save_audio_config(acfg):
                logger.info(f"[WebUI] TTS toggled to {new_val} and saved.")
            else:
                logger.error("[WebUI] Failed to save TTS toggle.")
            try:
                from core.processing import processore
                processore.configure(cfg_mgr.config)
            except Exception:
                pass
            return jsonify({"ok": True, "voice_status": new_val})
        except Exception as exc:
            logger.error(f"[WebUI] toggle_tts error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route("/api/audio/toggle/ptt", methods=["POST"])
    def toggle_ptt():
        """Toggle push_to_talk flag — mirrors F8 on the console."""
        try:
            sm = _sm()
            from core.audio.device_manager import get_audio_config, _save_audio_config
            acfg = get_audio_config()
            current_val = acfg.get("push_to_talk", False)
            new_val = not current_val
            
            acfg["push_to_talk"] = new_val
            if _save_audio_config(acfg):
                logger.info(f"[WebUI] PTT toggled to {new_val} and saved.")
            else:
                logger.error("[WebUI] Failed to save PTT toggle.")
            # Synchronize the live StateManager
            if sm is not None:
                sm.push_to_talk = new_val
            return jsonify({"ok": True, "push_to_talk": new_val})
        except Exception as exc:
            logger.error(f"[WebUI] toggle_ptt error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route("/api/audio/mode", methods=["POST"])
    def set_audio_mode():
        """Set audio_mode: console | web | auto"""
        try:
            data = request.get_json(force=True) or {}
            mode = data.get("mode", "auto")
            if mode not in ("console", "web", "auto"):
                return jsonify({"ok": False, "error": "Invalid mode. Use: console, web, auto"}), 400
            sm = _sm()
            if sm is not None:
                sm.audio_mode = mode
            cfg_mgr.config["audio_mode"] = mode
            cfg_mgr.save()
            return jsonify({"ok": True, "audio_mode": mode})
        except Exception as exc:
            logger.error(f"[WebUI] set_audio_mode error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route("/api/audio/test", methods=["POST"])
    def test_audio():
        """Tests the TTS engine (either local console or web preview)."""
        try:
            data = request.get_json(force=True) or {}
            text = data.get("text", "Test di Zentra Core, tutto funziona correttamente.")
            mode = data.get("mode", "console") # console or web
            
            from core.audio.device_manager import get_audio_config
            acfg = get_audio_config()

            if mode == "console":
                from core.audio.voice import speak
                # We force console playback
                threading.Thread(target=speak, args=(text,), daemon=True).start()
                return jsonify({"ok": True, "msg": "Speaking on console..."})
            
            else:
                from plugins.web_ui.routes_chat import generate_voice_file
                path = generate_voice_file(text, acfg)
                if path:
                    return jsonify({"ok": True, "url": f"/api/audio?t={int(time.time()*1000)}"})
                else:
                    return jsonify({"ok": False, "error": "Failed to generate audio file"})
                    
        except Exception as exc:
            logger.error(f"[WebUI] test_audio error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    # ── Audio Device Management API ───────────────────────────────────────────

    @app.route("/api/audio/devices", methods=["GET"])
    def get_audio_devices():
        """Returns available audio devices and current config_audio.json selection."""
        try:
            from core.audio.device_manager import list_devices, get_audio_config
            devices = list_devices()
            acfg = get_audio_config()
            return jsonify({
                "ok": True,
                "output_devices": devices["output"],
                "input_devices":  devices["input"],
                "selected_output_index": acfg.get("output_device_index", -1),
                "selected_output_name":  acfg.get("output_device_name",  ""),
                "selected_input_index":  acfg.get("input_device_index",  -1),
                "selected_input_name":   acfg.get("input_device_name",   ""),
                "last_scan":             acfg.get("last_scan",           ""),
            })
        except Exception as exc:
            logger.error(f"[WebUI] get_audio_devices error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route("/api/audio/devices/scan", methods=["POST"])
    def scan_audio_devices():
        """Triggers device scan + beep test on the best output device."""
        try:
            from core.audio.device_manager import scan_and_select
            cfg = scan_and_select(verbose=False)
            return jsonify({
                "ok": True,
                "output_device_index": cfg.get("output_device_index", -1),
                "output_device_name":  cfg.get("output_device_name",  ""),
                "input_device_index":  cfg.get("input_device_index",  -1),
                "input_device_name":   cfg.get("input_device_name",   ""),
                "last_scan":           cfg.get("last_scan",           ""),
            })
        except Exception as exc:
            logger.error(f"[WebUI] scan_audio_devices error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route("/api/audio/devices/select", methods=["POST"])
    def select_audio_device():
        """Manually sets output and/or input device index."""
        try:
            data = request.get_json(force=True) or {}
            from core.audio.device_manager import set_output_device, set_input_device, list_devices

            devs = list_devices()
            out_idx = data.get("output_index")
            in_idx  = data.get("input_index")

            if out_idx is not None:
                out_idx  = int(out_idx)
                out_name = next((d["name"] for d in devs["output"] if d["index"] == out_idx), "")
                set_output_device(out_idx, out_name)

            if in_idx is not None:
                in_idx  = int(in_idx)
                in_name = next((d["name"] for d in devs["input"] if d["index"] == in_idx), "")
                set_input_device(in_idx, in_name)

            return jsonify({"ok": True})
        except Exception as exc:
            logger.error(f"[WebUI] select_audio_device error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route("/api/audio/config", methods=["GET", "POST"])
    def manage_audio_config():
        """Gets or updates advanced audio settings in config_audio.json."""
        from core.audio.device_manager import get_audio_config, _save_audio_config
        
        if request.method == "GET":
            try:
                return jsonify({"ok": True, "config": get_audio_config()})
            except Exception as exc:
                return jsonify({"ok": False, "error": str(exc)}), 500
                
        if request.method == "POST":
            try:
                data = request.get_json(force=True) or {}
                cfg = get_audio_config()
                # Update allowed keys
                for k in ["voice_status", "listening_status", "piper_path", "onnx_model", 
                          "speed", "noise_scale", "noise_w", "sentence_silence",
                          "energy_threshold", "silence_timeout", "phrase_limit",
                          "input_device_index", "input_device_name", 
                          "output_device_index", "output_device_name",
                          "stt_source", "tts_destination"]:
                    if k in data:
                        cfg[k] = data[k]
                
                if "input_device_index" in data or "output_device_index" in data:
                    cfg["auto_select"] = False
                
                _save_audio_config(cfg)

                # Sync with running StateManager to prevent UI status from reverting
                sm = _sm()
                if sm:
                    if "stt_source" in data:
                        sm.stt_source = data["stt_source"]
                    if "tts_destination" in data:
                        sm.tts_destination = data["tts_destination"]

                return jsonify({"ok": True})
            except Exception as exc:
                logger.error(f"[WebUI] manage_audio_config POST error: {exc}")
                return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route("/api/logs/stream")
    def stream_logs():
        """SSE endpoint that streams latest Info and Debug logs."""
        from flask import Response, stream_with_context
        import time
        from datetime import datetime

        logger.debug("[WebUI-Logs] SSE Connection Request Received")

        def generate():
            # Get current log file paths (dynamic based on date)
            today = datetime.now().strftime('%Y-%m-%d')
            logs_dir = os.path.join(root_dir, "logs")
            info_path  = os.path.join(logs_dir, f"zentra_info_{today}.log")
            debug_path = os.path.join(logs_dir, f"zentra_debug_{today}.log")
            
            files = {
                'info':  {'path': info_path,  'pos': 0, 'label': 'INFO'},
                'debug': {'path': debug_path, 'pos': 0, 'label': 'DEBUG'}
            }

            # 1. SEND HISTORY (Last 50 lines per file)
            for k, f_info in files.items():
                if os.path.exists(f_info['path']):
                    try:
                        with open(f_info['path'], 'r', encoding='utf-8', errors='replace') as f:
                            lines = f.readlines()
                            f_info['pos'] = f.tell() # Mark current end
                            
                            # Send last 50 lines as history
                            for line in lines[-50:]:
                                if line.strip():
                                    data = json.dumps({
                                        "time":  "---", # Historical
                                        "level": f_info['label'],
                                        "text":  line.strip()
                                    })
                                    yield f"data: {data}\n\n"
                    except Exception as e:
                        logger.error(f"[WebUI] Log history error for {k}: {e}")

            # 2. POLL FOR NEW LINES
            while True:
                for k, f_info in files.items():
                    if not os.path.exists(f_info['path']):
                        continue
                    
                    try:
                        # Check if file was rotated or truncated
                        cur_size = os.path.getsize(f_info['path'])
                        if cur_size < f_info['pos']:
                            f_info['pos'] = 0 # reset
                        
                        with open(f_info['path'], 'r', encoding='utf-8', errors='replace') as f:
                            f.seek(f_info['pos'])
                            new_lines = f.readlines()
                            f_info['pos'] = f.tell()
                            
                            for line in new_lines:
                                if line.strip():
                                    data = json.dumps({
                                        "time":  datetime.now().strftime("%H:%M:%S"),
                                        "level": f_info['label'],
                                        "text":  line.strip()
                                    })
                                    yield f"data: {data}\n\n"
                    except Exception as e:
                        pass # Ignore transient errors during rotation
                
                time.sleep(1) # Poll for new lines every second

        return Response(stream_with_context(generate()), mimetype="text/event-stream")

    @app.route("/api/events")
    def stream_events():
        from flask import Response, stream_with_context
        import time
        sm = _sm()
        
        def generate():
            while True:
                if sm and sm.detected_voice_command:
                    cmd = sm.detected_voice_command
                    sm.detected_voice_command = None # Consumer clears it
                    yield f"data: {json.dumps({'type': 'voice_detected', 'text': cmd})}\n\n"
                
                # We could add more event types here (e.g. state changes)
                time.sleep(0.1)
        
        return Response(stream_with_context(generate()), mimetype="text/event-stream")
