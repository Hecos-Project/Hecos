from flask import render_template, request, redirect, url_for, jsonify, flash
from flask_login import login_user, logout_user, login_required
from zentra.core.auth.auth_manager import auth_mgr

def init_auth_routes(app, logger):

    @app.route('/login', methods=['GET', 'POST'])
    def login_page():
        from flask_login import current_user
        if current_user.is_authenticated:
            return redirect(url_for('chat_ui'))

        error = None
        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            remember = request.form.get('remember') == 'on'
            
            if auth_mgr.verify_password(username, password):
                user = auth_mgr.get_user_by_username(username)
                if user:
                    login_user(user, remember=remember)
                    logger.info(f"[WebUI Auth] User '{username}' logged in successfully. (Remember: {remember})")
                    return redirect(url_for('chat_ui'))
            
            # Auth failed
            logger.warning(f"[WebUI Auth] Failed login attempt for user '{username}'.")
            error = "Credenziali non valide. Riprova."

        return render_template('login.html', error=error)

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        return redirect(url_for('login_page'))
