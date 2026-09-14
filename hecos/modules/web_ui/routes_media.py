import os
import sys
import glob
from flask import request, jsonify
from hecos.core.constants import IMAGES_DIR, MEDIA_DIR

def init_media_routes(app, cfg_mgr, root_dir, logger, get_sm=None):
    def _sm():
        return get_sm() if callable(get_sm) else get_sm

    @app.route("/media/file")
    def serve_generic_file():
        """Serves any file from the local filesystem by its absolute path."""
        path = request.args.get("path")
        if not path:
            return jsonify({"ok": False, "error": "Path required"}), 400
        
        # Security: basic check (optional but good)
        if not os.path.exists(path):
            return jsonify({"ok": False, "error": f"File not found: {path}"}), 404
            
        allowed_exts = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg')
        if not path.lower().endswith(allowed_exts):
            # We still serve it if the user really wants, but maybe log it?
            pass

        try:
            from flask import send_file
            return send_file(path)
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500



    @app.route("/hecos/api/media/open-folder", methods=["POST"])
    def open_media_folder():
        """Opens the root media/ folder in the OS file explorer."""
        try:
            os.makedirs(MEDIA_DIR, exist_ok=True)
            from hecos.core.system.os_adapter import OSAdapter
            OSAdapter.open_path(MEDIA_DIR)
            return jsonify({"ok": True, "message": "Folder opened"})
        except Exception as exc:
            logger.error(f"[WebUI] open_media_folder error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route("/hecos/api/media/clear", methods=["POST"])
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
        from hecos.app.model_manager import ModelManager
        from hecos.modules.web_ui.routes_config_core import _invalidate_options_cache
        mm = ModelManager(cfg_mgr)
        categorized = mm.get_available_models()  # Live fetch → updates config YAML cache
        _invalidate_options_cache()              # Force next /hecos/options to rebuild
        # Return the fresh list directly so the JS can update without a second round-trip
        ollama = categorized.get("Ollama (Local)", [])
        cloud  = {k.replace("Cloud (","").replace(")","").lower(): v
                  for k, v in categorized.items() if "Cloud" in k}
        return jsonify({"ok": True, "ollama_models": ollama, "cloud_models": cloud})



