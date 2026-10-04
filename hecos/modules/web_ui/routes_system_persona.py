"""
routes_system_persona.py
────────────────────────────────────────────────────────────────────────────
Hecos WebUI — Persona & Avatar APIs
Registers:
  GET  /api/persona/avatar
  POST /api/persona/avatar/upload
────────────────────────────────────────────────────────────────────────────
"""
import os
import yaml
import urllib.parse
from flask import jsonify, request


def init_system_persona_routes(app, root_dir, logger):

    def _personas_dir():
        return os.path.join(root_dir, "hecos", "personas")

    @app.route("/api/persona/avatar", methods=["GET"])
    def persona_avatar_get():
        """Returns the avatar URL for a given persona name."""
        persona = request.args.get("persona", "").strip()
        if not persona:
            return jsonify({"ok": False, "error": "Missing persona name"}), 400

        from hecos.core.persona.persona_media import PersonaMediaManager
        avatar_info = PersonaMediaManager.resolve_avatar(persona)
        
        return jsonify({
            "ok": True, 
            "avatar_path": avatar_info.get("url", "/assets/Hecos_Logo_NBG.png"),
            "avatar_type": avatar_info.get("type", "image")
        })

    @app.route("/api/persona/avatar/upload", methods=["POST"])
    def persona_avatar_upload():
        """Legacy route: Handles image upload for a specific personality."""
        try:
            if "file" not in request.files:
                return jsonify({"ok": False, "error": "No file part"}), 400
            file    = request.files["file"]
            persona = request.form.get("persona")
            if not file or not persona:
                return jsonify({"ok": False, "error": "Missing file or persona name"}), 400

            from hecos.core.persona.persona_media import PersonaMediaManager
            res = PersonaMediaManager.upload_media(persona, file)
            new_avatar = PersonaMediaManager.set_avatar(persona, res["name"])
            
            logger.info(f"[WebUI] Avatar uploaded for persona {persona}: {res['name']}")
            return jsonify({"ok": True, "avatar_path": new_avatar["url"]})
        except Exception as exc:
            logger.error(f"[WebUI] persona_avatar_upload error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500
