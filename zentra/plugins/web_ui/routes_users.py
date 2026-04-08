from flask import jsonify, request
from core.auth.auth_manager import auth_mgr
from core.auth.decorators import admin_required

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
                return jsonify({"ok": False, "error": "Impossibile eliminare l'admin principale"}), 403

            success = auth_mgr.delete_user(username)
            if success:
                logger.info(f"[Auth API] Utente eliminato: {username}")
                return jsonify({"ok": True})
            else:
                return jsonify({"ok": False, "error": "Utente non trovato o protetto"}), 404
        except Exception as e:
            logger.error(f"[Auth API] Errore delete_user: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/zentra/api/users/<username>/password", methods=["PUT"])
    @admin_required
    def update_password(username):
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
