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
            # Estrai il flag custom Frontend per forzare il riavvio (o auto-save silenzioso)
            force_restart = incoming.pop("_force_restart", False)
            
            # DEBUG: Log exact state of plugins toggle
            p_state = incoming.get("plugins", {}).get("IMAGE_GEN", {}).get("enabled")
            logger.info(f"[CONFIG] Incoming Save Request. IMAGE_GEN enabled: {p_state}")
            
            if cfg_mgr.update_config(incoming):
                # Dynamically update the global translator language without reboot
                from zentra.core.i18n.translator import get_translator
                get_translator().set_language(incoming.get("language", "en"))
                
                # Keep state_manager in sync with toggles
                sm = _sm()
                if sm is not None:
                    from zentra.core.audio.device_manager import get_audio_config
                    acfg = get_audio_config()
                    sm.audio_mode = acfg.get("audio_mode", "auto")
                
                # Update the processor and registry at runtime
                try:
                    from zentra.core.processing import processore
                    from zentra.core.system import plugin_loader
                    processore.configure(incoming)
                    plugin_loader.update_capability_registry(incoming, debug_log=False)
                except Exception as e:
                    logger.debug(f"[WebUI] Processor runtime sync error: {e}")
                    
                # Gestione dell'inibitore del Monitor in base al trigger Frontend
                if not force_restart:
                    # Salvataggio silenzioso: scriviamo l'inibitore così il monitor INGNORA il file cambiato
                    try:
                        with open(".config_saved_by_app", "w") as f:
                            f.write("1")
                    except Exception: pass
                else:
                    # Salvataggio esplicito utente: rimuoviamo l'inibitore per forzare il riavvio del processo
                    if os.path.exists(".config_saved_by_app"):
                        try:
                            os.remove(".config_saved_by_app")
                        except Exception: pass
                        
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
        from zentra.core.media_config import get_media_config
        return jsonify(get_media_config())

    @app.route("/zentra/api/config/media", methods=["POST"])
    def post_media_config_api():
        try:
            incoming = request.get_json(force=True)
            if not isinstance(incoming, dict):
                 return jsonify({"ok": False, "error": "Invalid payload"}), 400
            
            from zentra.core.media_config import save_media_config, get_media_config
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

    @app.route("/zentra/config/routing", methods=["GET"])
    def get_routing_config():
        try:
            from zentra.config import load_yaml
            from zentra.config.schemas.routing_schema import RoutingOverrides
            path = os.path.join(root_dir, "zentra", "config", "data", "routing_overrides.yaml")
            model = load_yaml(path, RoutingOverrides)
            return jsonify(model.overrides)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/zentra/config/routing", methods=["POST"])
    def post_routing_config():
        try:
            incoming = request.get_json(force=True)
            if not isinstance(incoming, dict):
                return jsonify({"ok": False, "error": "Invalid payload"}), 400
            
            from zentra.config import save_yaml
            from zentra.config.schemas.routing_schema import RoutingOverrides
            path = os.path.join(root_dir, "zentra", "config", "data", "routing_overrides.yaml")
            
            # Re-validate and save
            model = RoutingOverrides(overrides=incoming)
            if save_yaml(path, model):
                logger.info("[WebUI] Routing overrides saved successfully.")
                return jsonify({"ok": True})
            return jsonify({"ok": False, "error": "Save failed"}), 500
        except Exception as exc:
            logger.error(f"[WebUI] POST /zentra/config/routing error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500
