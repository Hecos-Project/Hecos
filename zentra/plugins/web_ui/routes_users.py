import os
from flask import jsonify, request, send_file
from werkzeug.utils import secure_filename
from zentra.core.auth.auth_manager import auth_mgr
from zentra.core.auth.decorators import admin_required
from flask_login import current_user, login_required

def init_users_routes(app, logger):

    @app.route("/zentra/api/users", methods=["GET"])
    @admin_required
    def get_users():
        try:
            users = auth_mgr.get_all_users()
            return jsonify({"ok": True, "users": users})
        except Exception as e:
            logger.error(f"[Auth API] Errore get_users: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/zentra/api/users", methods=["POST"])
    @admin_required
    def create_user():
        try:
            data = request.get_json(force=True)
            username = data.get("username", "").strip()
            password = data.get("password", "")
            role = data.get("role", "guest")

            if not username or not password:
                return jsonify({"ok": False, "error": "Username e Password richiesti"}), 400

            success = auth_mgr.create_user(username, password, role)
            if success:
                logger.info(f"[Auth API] Creato nuovo utente: {username} ({role})")
                return jsonify({"ok": True})
            else:
                return jsonify({"ok": False, "error": "Utente già esistente o errore DB"}), 400
        except Exception as e:
            logger.error(f"[Auth API] Errore create_user: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/zentra/api/users/<username>", methods=["DELETE"])
    @admin_required
    def delete_user(username):
        try:
            if username == "admin":
                return jsonify({"ok": False, "error": "Impossibile eliminare l'admin"}), 403

            success = auth_mgr.delete_user(username)
            if success:
                from zentra.memory.user_vault_manager import delete_user_vault
                delete_user_vault(username)
                logger.info(f"[Auth API] Utente eliminato: {username}")
                return jsonify({"ok": True})
            else:
                return jsonify({"ok": False, "error": "Utente non trovato o protetto"}), 404
        except Exception as e:
            logger.error(f"[Auth API] Errore delete_user: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/zentra/api/users/<username>/password", methods=["PUT"])
    @login_required
    def update_password(username):
        # Admin can update anyone. Users can only update themselves.
        if current_user.role != "admin" and current_user.username != username:
            return jsonify({"ok": False, "error": "Non autorizzato"}), 403
            
        try:
            data = request.get_json(force=True)
            new_password = data.get("password")

            if not new_password:
                return jsonify({"ok": False, "error": "Password richiesta"}), 400

            success = auth_mgr.update_password(username, new_password)
            if success:
                logger.info(f"[Auth API] Password aggiornata per: {username}")
                return jsonify({"ok": True})
            else:
                return jsonify({"ok": False, "error": "Utente non trovato"}), 404
        except Exception as e:
            logger.error(f"[Auth API] Errore update_password: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    # --- NUOVI ENDPOINT PROFILO & AVATAR (Fase 3) ---

    @app.route("/zentra/api/users/<username>/profile", methods=["GET"])
    @login_required
    def get_profile(username):
        if username == "me":
            username = current_user.username
        if current_user.role != "admin" and current_user.username != username:
            return jsonify({"ok": False, "error": "Non autorizzato"}), 403
            
        profile = auth_mgr.get_profile(username)
        if profile:
            return jsonify({"ok": True, "profile": profile})
        return jsonify({"ok": False, "error": "Profilo non trovato"}), 404

    @app.route("/zentra/api/users/<username>/profile", methods=["PUT"])
    @login_required
    def update_profile(username):
        if username == "me":
            username = current_user.username
        if current_user.role != "admin" and current_user.username != username:
            return jsonify({"ok": False, "error": "Non autorizzato"}), 403
            
        data = request.get_json(force=True)
        if auth_mgr.update_profile(username, data):
            logger.info(f"[Auth API] Profilo aggiornato per: {username}")
            return jsonify({"ok": True})
        return jsonify({"ok": False, "error": "Errore aggiornamento profilo"}), 400

    @app.route("/zentra/api/users/<username>/avatar", methods=["POST"])
    @login_required
    def upload_avatar(username):
        if username == "me":
            username = current_user.username
        if current_user.role != "admin" and current_user.username != username:
            return jsonify({"ok": False, "error": "Non autorizzato"}), 403
            
        if 'file' not in request.files:
            return jsonify({"ok": False, "error": "Nessun file inviato"}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({"ok": False, "error": "Filename vuoto"}), 400
            
        if file:
            try:
                from zentra.memory.user_vault_manager import get_vault_path
                vault = get_vault_path(username)
                os.makedirs(vault, exist_ok=True)
                
                # We always save it as avatar.jpg regardless of original name for simplicity
                avatar_path = os.path.join(vault, "avatar.jpg")
                file.save(avatar_path)
                
                # Update DB to point to the avatar endpoint
                auth_mgr.update_profile(username, {"avatar_path": f"/zentra/api/users/{username}/avatar"})
                logger.info(f"[Auth API] Avatar caricato per: {username}")
                return jsonify({"ok": True, "avatar_path": f"/zentra/api/users/{username}/avatar"})
            except Exception as e:
                logger.error(f"[Auth API] Errore upload avatar: {e}")
                return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/zentra/api/users/<username>/avatar", methods=["GET"])
    @login_required
    def get_avatar(username):
        if username == "me":
            username = current_user.username
        # We allow everyone logged in to see avatars (useful for UI lists)
        from zentra.memory.user_vault_manager import get_vault_path
        vault = get_vault_path(username)
        avatar_path = os.path.join(vault, "avatar.jpg")
        
        if os.path.exists(avatar_path):
            return send_file(avatar_path, mimetype='image/jpeg')
            
        # Fallback to no-avatar default? Not implemented yet, just 404 for now
        return jsonify({"error": "No avatar"}), 404
