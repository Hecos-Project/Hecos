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

    @app.route("/api/persona/avatar", methods=["GET"])
    def persona_avatar_get():
        """Returns the avatar URL for a given persona name."""
        persona = request.args.get("persona", "").strip()
        if not persona:
            return jsonify({"ok": False, "error": "Missing persona name"}), 400

        if persona.endswith(".yaml"):
            persona = persona[:-5]

        p_dir   = os.path.join(root_dir, "hecos", "personality")
        p_file  = os.path.join(p_dir, f"{persona}.yaml")
        default = "/assets/Hecos_Logo_NBG.png"

        if not os.path.exists(p_file):
            return jsonify({"ok": True, "avatar_path": default})

        try:
            with open(p_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            ai = data.get("avatar_image", "")
            if ai:
                encoded = urllib.parse.quote(ai)
                return jsonify({"ok": True, "avatar_path": f"/assets/{encoded}"})
            return jsonify({"ok": True, "avatar_path": default})
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route("/api/persona/avatar/upload", methods=["POST"])
    def persona_avatar_upload():
        """Handles image upload for a specific personality."""
        try:
            if "file" not in request.files:
                return jsonify({"ok": False, "error": "No file part"}), 400
            file    = request.files["file"]
            persona = request.form.get("persona")
            if not file or not persona:
                return jsonify({"ok": False, "error": "Missing file or persona name"}), 400

            # Prepare directories inside hecos/assets/avatars/
            from werkzeug.utils import secure_filename
            assets_dir        = os.path.join(root_dir, "hecos", "assets")
            avatar_base_dir   = os.path.join(assets_dir, "avatars")
            safe_persona      = secure_filename(persona)
            persona_avatar_dir = os.path.join(avatar_base_dir, safe_persona)
            os.makedirs(persona_avatar_dir, exist_ok=True)

            filename  = secure_filename(file.filename)
            save_path = os.path.join(persona_avatar_dir, filename)
            file.save(save_path)

            # Update the persona YAML with the new avatar path
            p_dir  = os.path.join(root_dir, "hecos", "personality")
            p_file = os.path.join(p_dir, f"{persona}.yaml")
            if os.path.exists(p_file):
                with open(p_file, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                data["avatar_image"] = f"avatars/{safe_persona}/{filename}"
                with open(p_file, "w", encoding="utf-8") as f:
                    yaml.dump(data, f, allow_unicode=True, sort_keys=False)

            logger.info(f"[WebUI] Avatar uploaded for persona {persona}: {filename}")
            return jsonify({"ok": True, "avatar_path": f"/assets/avatars/{safe_persona}/{filename}"})
        except Exception as exc:
            logger.error(f"[WebUI] persona_avatar_upload error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500
