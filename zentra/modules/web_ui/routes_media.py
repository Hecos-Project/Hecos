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
