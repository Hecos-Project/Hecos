import os
from flask import request, jsonify, render_template

def init_routes(app, cfg_mgr, root_dir, logger):
    
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
            
        ollama_models = list(cfg.get("backend", {}).get("ollama", {}).get("available_models", {}).values())
        personalita   = list(cfg.get("ai", {}).get("available_personalities", {}).values())
        cloud_models  = {
            p: cfg.get("llm", {}).get("providers", {}).get(p, {}).get("models", [])
            for p in ("openai", "anthropic", "groq", "gemini")
        }
        return jsonify({
            "piper_voices": onnx_files,
            "piper_dir":    piper_path_dir,
            "ollama_models": ollama_models,
            "personalities": personalita,
            "cloud_models":  cloud_models
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

            # System Global Status (F4/F5)
            mic_status = "ON" if listen.get("listening_status") else "OFF"
            tts_status = "ON" if voice.get("voice_status") else "OFF"

            # Check if Bridge TTS is also set (for the chip itself, we follow the voice engine)
            # If the user wants specific bridge info, we could add it, but 'tts_status' is what they see.

            from datetime import datetime
            config_path = os.path.join(root_dir, "config.json")
            mtime = os.path.getmtime(config_path) if os.path.exists(config_path) else 0
            ts    = datetime.fromtimestamp(mtime).strftime("%H:%M:%S") if mtime else "?"

            return jsonify({
                "backend": backend.upper(),
                "model":   model,
                "bridge":  ", ".join(flags) if flags else "default",
                "mic":     mic_status,
                "tts":     tts_status,
                "config":  f"last save {ts}",
            })
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500
