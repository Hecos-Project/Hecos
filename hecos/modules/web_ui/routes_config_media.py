"""
routes_config_media.py
─────────────────────────────────────────────────────────────────────────────
Hecos WebUI — Media Configuration Routes
Handles the media.yaml / plugins.MEDIA_PLAYER persistence layer,
including optional API key save-to-.env functionality.
Isolated here to avoid cross-contamination with system.yaml save paths.
─────────────────────────────────────────────────────────────────────────────
"""
from flask import request, jsonify


def init_config_media_routes(app, logger):
    """Register media config API routes."""

    @app.route("/hecos/api/config/media", methods=["GET"])
    def get_media_config_api():
        from hecos.core.media_config import get_media_config
        return jsonify(get_media_config())

    @app.route("/hecos/api/config/media", methods=["POST"])
    def post_media_config_api():
        try:
            incoming = request.get_json(force=True)
            if not isinstance(incoming, dict):
                return jsonify({"ok": False, "error": "Invalid payload"}), 400

            from hecos.core.media_config import save_media_config, get_media_config
            cfg  = get_media_config()

            # Extract image_gen block before deep-merge
            igen = incoming.get("image_gen", {})
            save_to_env = igen.pop("_internal_save_to_env", False)
            logger.info(f"[WebUI] Media Save. save_to_env={save_to_env}")

            # Deep update: merge dicts, replace scalars
            for key, val in incoming.items():
                if isinstance(val, dict) and key in cfg and isinstance(cfg[key], dict):
                    cfg[key].update(val)
                else:
                    cfg[key] = val

            # Optionally persist API key to .env key pool
            if save_to_env:
                try:
                    api_key  = igen.get("api_key",  "").strip()
                    provider = igen.get("provider", "huggingface").strip().lower()
                    comment  = igen.get("api_key_comment", "").strip()
                    logger.info(f"[WebUI] Attempting key persistence. Provider={provider}, KeyLen={len(api_key)}")
                    if api_key:
                        from hecos.core.keys.key_manager import get_key_manager
                        res = get_key_manager().add_key(provider, api_key, comment, save_to_env=True)
                        logger.info(f"[WebUI] Key persistence result: {res}")
                    else:
                        logger.warning("[WebUI] Save to .env requested but api_key is empty.")
                except Exception as e:
                    logger.error(f"[WebUI] Error saving key to .env: {e}")

            if save_media_config(cfg):
                logger.info("[WebUI] Media configuration saved successfully.")
                return jsonify({"ok": True})
            return jsonify({"ok": False, "error": "Save failed"}), 500

        except Exception as exc:
            logger.error(f"[WebUI] POST /hecos/api/config/media error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500
