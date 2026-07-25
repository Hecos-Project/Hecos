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

        if persona.endswith(".yaml"):
            persona = persona[:-5]

        default = "/assets/Hecos_Logo_NBG.png"
        p_dir   = os.path.join(_personas_dir(), persona)

        if not os.path.isdir(p_dir):
            return jsonify({"ok": True, "avatar_path": default})

        # Find first image in the avatars subfolder
        avatars_dir = os.path.join(p_dir, "avatars")
        if os.path.isdir(avatars_dir):
            try:
                for img_file in sorted(os.listdir(avatars_dir)):
                    if img_file.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                        rel = f"{urllib.parse.quote(persona)}/avatars/{urllib.parse.quote(img_file)}"
                        return jsonify({"ok": True, "avatar_path": "/personas/" + rel})
            except Exception as exc:
                return jsonify({"ok": False, "error": str(exc)}), 500

        return jsonify({"ok": True, "avatar_path": default})

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

            from werkzeug.utils import secure_filename
            safe_persona       = secure_filename(persona.replace(".yaml", ""))
            persona_avatar_dir = os.path.join(_personas_dir(), safe_persona, "avatars")
            os.makedirs(persona_avatar_dir, exist_ok=True)

            filename  = secure_filename(file.filename)
            save_path = os.path.join(persona_avatar_dir, filename)
            file.save(save_path)

            rel_path = f"/personas/{urllib.parse.quote(safe_persona)}/avatars/{urllib.parse.quote(filename)}"

            logger.info(f"[WebUI] Avatar uploaded for persona {persona}: {filename}")
            return jsonify({"ok": True, "avatar_path": rel_path})
        except Exception as exc:
            logger.error(f"[WebUI] persona_avatar_upload error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500
