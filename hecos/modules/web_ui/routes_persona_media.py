"""
routes_persona_media.py
────────────────────────────────────────────────────────────────────────────
Hecos WebUI — Soul Media Library APIs
Provides endpoints for the Persona Config panel and Chat avatars.
────────────────────────────────────────────────────────────────────────────
"""
import os
import shutil
from flask import jsonify, request
from werkzeug.utils import secure_filename
from hecos.core.persona.persona_media import PersonaMediaManager
from hecos.core.system.os_adapter import OSAdapter
from hecos.core.logging import logger

def init_persona_media_routes(app, root_dir, get_sm=None):
    
    @app.route("/api/persona/media", methods=["GET"])
    def get_persona_media():
        persona = request.args.get("persona", "").strip()
        if not persona:
            return jsonify({"ok": False, "error": "Missing persona name"}), 400
            
        avatar = PersonaMediaManager.resolve_avatar(persona)
        media_list = PersonaMediaManager.list_media(persona)
        
        return jsonify({
            "ok": True,
            "avatar": avatar,
            "media": media_list
        })
        
    @app.route("/api/persona/media/upload", methods=["POST"])
    def upload_persona_media():
        persona = request.form.get("persona", "").strip()
        if not persona:
            return jsonify({"ok": False, "error": "Missing persona"}), 400
            
        set_as_avatar = request.form.get("set_as_avatar", "false").lower() == "true"
        
        if "file" not in request.files:
            return jsonify({"ok": False, "error": "No files provided"}), 400
            
        files = request.files.getlist("file")
        results = []
        
        try:
            for file_obj in files:
                if file_obj.filename:
                    res = PersonaMediaManager.upload_media(persona, file_obj)
                    results.append(res)
                    
                    if set_as_avatar and len(results) == 1:
                        PersonaMediaManager.set_avatar(persona, res["name"])
                        
            return jsonify({"ok": True, "uploaded": results})
        except Exception as e:
            logger.error(f"[PersonaMedia] Upload error for {persona}: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/persona/media/delete", methods=["POST"])
    def delete_persona_media():
        data = request.get_json(force=True) or {}
        persona = data.get("persona", "").strip()
        filenames = data.get("filenames", [])
        
        if not persona or not filenames:
            return jsonify({"ok": False, "error": "Missing persona or filenames"}), 400
            
        try:
            deleted = PersonaMediaManager.delete_media(persona, filenames)
            return jsonify({"ok": True, "deleted_count": deleted})
        except Exception as e:
            logger.error(f"[PersonaMedia] Delete error for {persona}: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/persona/media/set-avatar", methods=["POST"])
    def set_persona_avatar():
        data = request.get_json(force=True) or {}
        persona = data.get("persona", "").strip()
        filename = data.get("filename", "").strip()
        
        if not persona or not filename:
            return jsonify({"ok": False, "error": "Missing persona or filename"}), 400
            
        try:
            new_avatar = PersonaMediaManager.set_avatar(persona, filename)
            return jsonify({"ok": True, "avatar": new_avatar})
        except FileNotFoundError:
            return jsonify({"ok": False, "error": "File not found"}), 404
        except Exception as e:
            logger.error(f"[PersonaMedia] Set avatar error for {persona}: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/persona/media/rename", methods=["POST"])
    def rename_persona_media():
        data = request.get_json(force=True) or {}
        persona = data.get("persona", "").strip()
        old_name = data.get("old_name", "").strip()
        new_name = data.get("new_name", "").strip()
        
        if not persona or not old_name or not new_name:
            return jsonify({"ok": False, "error": "Missing parameters"}), 400
            
        try:
            res = PersonaMediaManager.rename_media(persona, old_name, new_name)
            return jsonify({"ok": True, "item": res})
        except FileExistsError:
            return jsonify({"ok": False, "error": "A file with this name already exists"}), 409
        except Exception as e:
            logger.error(f"[PersonaMedia] Rename error for {persona}: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/persona/media/open-folder", methods=["POST"])
    def open_persona_media_folder():
        data = request.get_json(force=True) or {}
        persona = data.get("persona", "").strip()
        
        if not persona:
            return jsonify({"ok": False, "error": "Missing persona name"}), 400
            
        try:
            p_dir = PersonaMediaManager._persona_dir(persona)
            PersonaMediaManager._ensure_dirs(p_dir)
            OSAdapter.open_path(p_dir)
            return jsonify({"ok": True})
        except Exception as e:
            logger.error(f"[PersonaMedia] Open folder error for {persona}: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500
