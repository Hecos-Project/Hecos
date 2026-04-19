import os
import sys
import glob
from flask import request, jsonify
from zentra.core.constants import IMAGES_DIR, MEDIA_DIR

def init_media_routes(app, cfg_mgr, root_dir, logger, get_sm=None):
    def _sm():
        return get_sm() if callable(get_sm) else get_sm

    @app.route("/zentra/api/media/models", methods=["GET"])
    def get_media_models():
        """Returns available image generation models for the specified provider."""
        provider = request.args.get("provider", "pollinations")
        try:
            from zentra.core.media.image_providers import get_models_for_provider
            models = get_models_for_provider(provider)
            return jsonify({"ok": True, "provider": provider, "models": models})
        except Exception as exc:
            logger.error(f"[WebUI] get_media_models error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route("/zentra/api/media/open-folder", methods=["POST"])
    def open_media_folder():
        """Opens the root media/ folder in the OS file explorer."""
        try:
            os.makedirs(MEDIA_DIR, exist_ok=True)
            from zentra.core.system.os_adapter import OSAdapter
            OSAdapter.open_path(MEDIA_DIR)
            return jsonify({"ok": True, "message": "Folder opened"})
        except Exception as exc:
            logger.error(f"[WebUI] open_media_folder error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route("/zentra/api/media/clear", methods=["POST"])
    def clear_media_vault():
        """Deletes all generated items in centralized media/images/."""
        try:
            if not os.path.exists(IMAGES_DIR):
                return jsonify({"ok": True, "deleted": 0})
            
            files = glob.glob(os.path.join(IMAGES_DIR, "*"))
            count = 0
            for f in files:
                if os.path.isfile(f):
                    try:
                        os.remove(f)
                        count += 1
                    except Exception as e:
                        logger.error(f"[WebUI] Could not delete {f}: {e}")
            return jsonify({"ok": True, "deleted": count})
        except Exception as exc:
            logger.error(f"[WebUI] clear_media_vault error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route("/api/models/refresh", methods=["POST"])
    def refresh_models():
        from app.model_manager import ModelManager
        mm = ModelManager(cfg_mgr)
        mm.get_available_models() # This updates the cache in config
        return jsonify({"ok": True})

    @app.route("/zentra/api/media/refine-prompt", methods=["POST"])
    def refine_media_prompt():
        """Refines a draft prompt using Zentra's Brain for Flux."""
        try:
            data = request.json or {}
            prompt = data.get("prompt", "").strip()
            instructions = data.get("instructions", "").strip()
            if not prompt:
                return jsonify({"ok": False, "error": "Prompt is empty"})
                
            from zentra.core.llm import client
            from app.model_manager import ModelManager
            
            system_prompt = (
                "You are an expert prompt engineer specializing in the Flux image generation model. "
                "Flux prefers detailed, natural language descriptions over comma-separated tags. "
                f"{instructions}"
            )
            user_msg = f"Optimize this prompt for Flux: {prompt}"
            
            main_cfg = cfg_mgr.config
            effective_backend_type, effective_default_model = ModelManager.get_effective_model_info(main_cfg)
            backend_config = main_cfg.get('backend', {}).get(effective_backend_type, {}).copy()
            backend_config['model'] = effective_default_model
            backend_config['backend_type'] = effective_backend_type
            llm_cfg = main_cfg.get('llm', {})
            
            refined = client.generate(system_prompt, user_msg, backend_config, llm_cfg)
            
            if refined and not isinstance(refined, dict) and not refined.startswith("⚠️"):
                cleaned = refined.strip().strip('"').strip("'")
                return jsonify({"ok": True, "refined": cleaned})
                
            return jsonify({"ok": False, "error": "LLM returned empty or error"})
            
        except Exception as exc:
            logger.error(f"[WebUI] refine_media_prompt error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500
