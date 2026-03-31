import os
import json
from flask import request, jsonify, render_template

def init_config_routes(app, cfg_mgr, root_dir, logger, get_sm=None):
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

    @app.route("/zentra/config", methods=["POST"])
    def post_config():
        try:
            incoming = request.get_json(force=True)
            if not isinstance(incoming, dict):
                return jsonify({"ok": False, "error": "Invalid payload"}), 400
            
            # DEBUG: Log exact state of plugins toggle
            p_state = incoming.get("plugins", {}).get("IMAGE_GEN", {}).get("enabled")
            logger.info("CONFIG", f"Incoming Save Request. IMAGE_GEN enabled: {p_state}")
            
            if cfg_mgr.update_config(incoming):
                # Dynamically update the global translator language without reboot
                from core.i18n.translator import get_translator
                get_translator().set_language(incoming.get("language", "en"))
                
                # Keep state_manager in sync with toggles
                # Note: audio_mode is in config_audio.json, not here
                sm = _sm()
                if sm is not None:
                    from core.audio.device_manager import get_audio_config
                    acfg = get_audio_config()
                    sm.audio_mode = acfg.get("audio_mode", "auto")
                
                # Update the processor and registry at runtime
                try:
                    from core.processing import processore
                    from core.system import plugin_loader
                    processore.configure(incoming)
                    plugin_loader.update_capability_registry(incoming, debug_log=False)
                except Exception as e:
                    logger.debug(f"[WebUI] Processor runtime sync error: {e}")
                    
                return jsonify({"ok": True})
            return jsonify({"ok": False, "error": "Save failed"}), 500
        except Exception as exc:
            logger.error(f"[WebUI] POST /config error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

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
        
        # Ensure config.json is in sync with filesystem personalities before returning
        cfg_mgr.sync_available_personalities()
        cfg = cfg_mgr.reload()
        personalita = list(cfg.get("ai", {}).get("available_personalities", {}).values())
        
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

    @app.route("/zentra/api/config/media", methods=["GET"])
    def get_media_config_api():
        from core.media_config import get_media_config
        return jsonify(get_media_config())

    @app.route("/zentra/api/config/media", methods=["POST"])
    def post_media_config_api():
        try:
            incoming = request.get_json(force=True)
            if not isinstance(incoming, dict):
                 return jsonify({"ok": False, "error": "Invalid payload"}), 400
            
            from core.media_config import save_media_config, get_media_config
            cfg = get_media_config()
            
            # Simple deep update
            for key, val in incoming.items():
                if isinstance(val, dict) and key in cfg and isinstance(cfg[key], dict):
                    cfg[key].update(val)
                else:
                    cfg[key] = val
                    
            if save_media_config(cfg):
                logger.info("[WebUI] Media configuration saved successfully.")
                return jsonify({"ok": True})
            return jsonify({"ok": False, "error": "Save failed"}), 500
        except Exception as exc:
            logger.error(f"[WebUI] POST /zentra/api/config/media error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500
