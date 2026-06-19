import os
from flask import jsonify, request, send_file
from werkzeug.utils import secure_filename
from hecos.core.auth.auth_manager import auth_mgr
from hecos.core.auth.decorators import admin_required
from flask_login import current_user, login_required

def init_users_routes(app, logger):

    @app.route("/hecos/api/users", methods=["GET"])
    @admin_required
    def get_users():
        try:
            users = auth_mgr.get_all_users()
            return jsonify({"ok": True, "users": users})
        except Exception as e:
            logger.error(f"[Auth API] Errore get_users: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/hecos/api/users", methods=["POST"])
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

    @app.route("/hecos/api/users/<username>", methods=["DELETE"])
    @admin_required
    def delete_user(username):
        try:
            if username == "admin":
                return jsonify({"ok": False, "error": "Impossibile eliminare l'admin"}), 403

            success = auth_mgr.delete_user(username)
            if success:
                from hecos.memory.user_vault_manager import delete_user_vault
                delete_user_vault(username)
                logger.info(f"[Auth API] Utente eliminato: {username}")
                return jsonify({"ok": True})
            else:
                return jsonify({"ok": False, "error": "Utente non trovato o protetto"}), 404
        except Exception as e:
            logger.error(f"[Auth API] Errore delete_user: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/hecos/api/users/<username>/password", methods=["PUT"])
    @login_required
    def update_password(username):
        # Admin can update anyone. Users can only update themselves.
        if current_user.role != "admin" and current_user.username != username:
            return jsonify({"ok": False, "error": "Non autorizzato"}), 403
            
        try:
            data = request.get_json(force=True)
            new_password = data.get("password")
            current_pass = data.get("current_password")

            if not new_password:
                return jsonify({"ok": False, "error": "Nuova password richiesta"}), 400

            # Security: If a user is changing their OWN password, they MUST provide the current one.
            # Admins changing OTHER users' passwords can skip this check.
            is_self = (current_user.username == username)
            if is_self:
                if not current_pass or not auth_mgr.verify_password(username, current_pass):
                    return jsonify({"ok": False, "error": "Password attuale errata o mancante"}), 403

            success = auth_mgr.update_password(username, new_password)
            if success:
                logger.info(f"[Auth API] Password aggiornata per: {username} (Auto-verified: {is_self})")
                return jsonify({"ok": True})
            else:
                return jsonify({"ok": False, "error": "Utente non trovato"}), 404
        except Exception as e:
            logger.error(f"[Auth API] Errore update_password: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    # --- NUOVI ENDPOINT PROFILO & AVATAR (Fase 3) ---

    @app.route("/hecos/api/users/<username>/profile", methods=["GET"])
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

    @app.route("/hecos/api/users/<username>/profile", methods=["PUT"])
    @login_required
    def update_profile(username):
        if username == "me":
            username = current_user.username
        if current_user.role != "admin" and current_user.username != username:
            return jsonify({"ok": False, "error": "Non autorizzato"}), 403
            
        data = request.get_json(force=True)
        if auth_mgr.update_profile(username, data):
            logger.info(f"[Auth API] Profilo aggiornato per: {username}")
            # --- Language sync fix: apply the new language immediately ---
            new_lang = data.get("preferred_language")
            if new_lang:
                try:
                    # 1. Update the live translator instance
                    from hecos.core.i18n import translator
                    translator.get_translator().set_language(new_lang)
                    
                    # 2. Update and persist the global system configuration
                    if hasattr(app, 'hecos_config_manager'):
                        app.hecos_config_manager.set(new_lang, "language")
                        app.hecos_config_manager.save()
                    
                    logger.info(f"[Auth API] Lingua applicata e salvata in system.yaml: {new_lang}")
                except Exception as lang_e:
                    logger.warning(f"[Auth API] Lingua salvata in DB ma errore nella persistenza globale: {lang_e}")
            return jsonify({"ok": True})
        return jsonify({"ok": False, "error": "Errore aggiornamento profilo"}), 400

    @app.route("/hecos/api/users/<username>/avatar", methods=["POST"])
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
                from hecos.memory.user_vault_manager import get_vault_path
                vault = get_vault_path(username)
                os.makedirs(vault, exist_ok=True)
                
                # We always save it as avatar.jpg regardless of original name for simplicity
                avatar_path = os.path.join(vault, "avatar.jpg")
                file.save(avatar_path)
                
                # Update DB to point to the avatar endpoint
                auth_mgr.update_profile(username, {"avatar_path": f"/hecos/api/users/{username}/avatar"})
                logger.info(f"[Auth API] Avatar caricato per: {username}")
                return jsonify({"ok": True, "avatar_path": f"/hecos/api/users/{username}/avatar"})
            except Exception as e:
                logger.error(f"[Auth API] Errore upload avatar: {e}")
                return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/hecos/api/users/<username>/avatar", methods=["GET"])
    @login_required
    def get_avatar(username):
        if username == "me":
            username = current_user.username
        # We allow everyone logged in to see avatars (useful for UI lists)
        from hecos.memory.user_vault_manager import get_vault_path
        vault = get_vault_path(username)
        avatar_path = os.path.join(vault, "avatar.jpg")
        
        if os.path.exists(avatar_path):
            return send_file(avatar_path, mimetype='image/jpeg')
            
        # Fallback to no-avatar default? Not implemented yet, just 404 for now
        return jsonify({"error": "No avatar"}), 404

    # ── Backup / Restore ──────────────────────────────────────────────────────

    @app.route("/hecos/api/users/backup", methods=["GET"])
    @admin_required
    def users_backup():
        """Export all user profiles (no password hashes) as JSON backup."""
        try:
            all_users = auth_mgr.get_all_users()
            profiles = []
            for u in all_users:
                profile = auth_mgr.get_profile(u["username"])
                if profile:
                    # Never export password hash
                    profile.pop("password_hash", None)
                    profiles.append(profile)
            return jsonify({"ok": True, "users": profiles, "count": len(profiles)})
        except Exception as e:
            logger.error(f"[Auth API] Errore users_backup: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/hecos/api/users/restore", methods=["POST"])
    @admin_required
    def users_restore():
        """
        Restore user profiles from a backup bundle.
        Body: { users: [...], mode: 'merge' | 'replace' }
        - merge  (default): update profile if user exists, skip creation of new users
        - replace: for existing users, overwrite profile; for new users, create with temp password
        NOTE: Passwords are NEVER exported, so restored accounts that don't exist get a
              temporary password 'hecos' which the admin should change immediately.
        """
        try:
            data  = request.get_json(force=True) or {}
            users = data.get("users", [])
            mode  = data.get("mode", "merge")

            if not isinstance(users, list):
                return jsonify({"ok": False, "error": "Invalid format"}), 400

            imported = 0
            skipped  = 0
            for u in users:
                username = u.get("username", "").strip()
                if not username or username == "admin":
                    skipped += 1
                    continue

                existing = auth_mgr.get_user_by_username(username)

                if existing:
                    # Always update profile fields for existing users
                    profile_fields = {k: v for k, v in u.items()
                                      if k not in ("id", "username", "password_hash", "avatar_path")}
                    auth_mgr.update_profile(username, profile_fields)
                    imported += 1
                elif mode == "replace":
                    # Create missing user with temporary password
                    role = u.get("role", "guest")
                    auth_mgr.create_user(username, "hecos", role)
                    profile_fields = {k: v for k, v in u.items()
                                      if k not in ("id", "username", "password_hash", "avatar_path")}
                    auth_mgr.update_profile(username, profile_fields)
                    imported += 1
                else:
                    skipped += 1

            return jsonify({"ok": True, "imported": imported, "skipped": skipped}), 201
        except Exception as e:
            logger.error(f"[Auth API] Errore users_restore: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/hecos/api/users/<username>/export", methods=["GET"])
    @login_required
    def export_user(username):
        """Export a single user's profile as JSON (admin or own profile only)."""
        if username == "me":
            username = current_user.username
        if current_user.role != "admin" and current_user.username != username:
            return jsonify({"ok": False, "error": "Non autorizzato"}), 403
        try:
            profile = auth_mgr.get_profile(username)
            if not profile:
                return jsonify({"ok": False, "error": "Utente non trovato"}), 404
            profile.pop("password_hash", None)
            return jsonify({"ok": True, "user": profile})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/hecos/api/users/import_single", methods=["POST"])
    @admin_required
    def import_user_single():
        """
        Import/update a single user profile from JSON.
        Body: { user: {...} }
        If the user doesn't exist, creates them with temp password 'hecos'.
        """
        try:
            data = request.get_json(force=True) or {}
            u    = data.get("user", {})
            username = u.get("username", "").strip()
            if not username:
                return jsonify({"ok": False, "error": "Username mancante"}), 400
            if username == "admin" and current_user.username != "admin":
                return jsonify({"ok": False, "error": "Non puoi importare l'account admin"}), 403

            existing = auth_mgr.get_user_by_username(username)
            if not existing:
                role = u.get("role", "guest")
                auth_mgr.create_user(username, "hecos", role)

            profile_fields = {k: v for k, v in u.items()
                              if k not in ("id", "username", "password_hash", "avatar_path")}
            auth_mgr.update_profile(username, profile_fields)
            created = not existing
            return jsonify({"ok": True, "created": created, "username": username}), 201
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

