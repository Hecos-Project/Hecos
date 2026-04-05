from functools import wraps
from flask import redirect, url_for, jsonify, request
from flask_login import current_user

def admin_required(f):
    """
    Decoratore che verifica sia l'esistenza della sessione (tramite f)
    sia che il ruolo dell'utente loggato sia 'admin'.
    Invia un errore JSON o reindirizza a home in caso di mancanza permessi.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            # Se la richiesta è AJAX o API, ritorna JSON
            if request.path.startswith('/api/'):
                return jsonify({"ok": False, "error": "Authentication required."}), 401
            return redirect(url_for('web_bp.login_page'))
            
        if getattr(current_user, 'role', 'guest') != 'admin':
            if request.path.startswith('/api/'):
                return jsonify({"ok": False, "error": "Admin privileges required."}), 403
            return redirect(url_for('web_bp.chat_ui'))
            
        return f(*args, **kwargs)
    return decorated_function
