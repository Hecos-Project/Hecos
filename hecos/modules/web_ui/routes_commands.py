"""
WEB_UI Plugin — Slash Commands Routes
Provides endpoints for the frontend Command Palette to list, search, and run commands.
"""

from flask import request, jsonify
from flask_login import login_required, current_user
import logging

_log = logging.getLogger("HecosWebUICommands")


def init_commands_routes(app, config_manager, logger, get_state_manager):

    @app.route('/api/commands/list', methods=['GET'])
    @login_required
    def api_commands_list():
        """Returns all registered commands."""
        try:
            from hecos.core.commands.registry import get_registry
            registry = get_registry(config=config_manager.config)
            cmds = registry.get_all()

            # Filter out admin commands if current user is not admin
            role = getattr(current_user, "role", "user")
            if role != "admin":
                cmds = [c for c in cmds if c.get("requires_auth", "any") != "admin"]

            # Sanitize: Remove non-serializable fields like '_handler'
            safe_cmds = []
            for c in cmds:
                safe_cmd = {k: v for k, v in c.items() if not callable(v) and k != "_handler"}
                safe_cmds.append(safe_cmd)

            return jsonify({"ok": True, "commands": safe_cmds})
        except Exception as e:
            _log.error(f"[API Commands] Error listing: {e}", exc_info=True)
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route('/api/commands/search', methods=['GET'])
    @login_required
    def api_commands_search():
        """Full-text search on commands."""
        try:
            q = request.args.get('q', '').strip()
            from hecos.core.commands.registry import get_registry
            registry = get_registry(config=config_manager.config)
            
            if not q:
                cmds = registry.get_all()
            else:
                cmds = registry.search(q)

            # Filter out admin commands if current user is not admin
            role = getattr(current_user, "role", "user")
            if role != "admin":
                cmds = [c for c in cmds if c.get("requires_auth", "any") != "admin"]

            # Sanitize: Remove non-serializable fields like '_handler'
            safe_cmds = []
            for c in cmds:
                safe_cmd = {k: v for k, v in c.items() if not callable(v) and k != "_handler"}
                safe_cmds.append(safe_cmd)

            return jsonify({"ok": True, "commands": safe_cmds})
        except Exception as e:
            _log.error(f"[API Commands] Error searching: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route('/api/commands/run', methods=['POST'])
    @login_required
    def api_commands_run():
        """
        Execute a command directly.
        Expected JSON: {"cmd": "/img foto di gatto", "context": "chat"|"flows"}
        """
        try:
            data = request.json or {}
            raw_input = data.get("cmd", "").strip()
            page_context = data.get("context", "chat")

            if not raw_input:
                return jsonify({"ok": False, "error": "No command provided"}), 400

            # Prepare execution context
            role = getattr(current_user, "role", "user")
            user_id = getattr(current_user, "id", "admin")
            session_id = data.get("session_id")
            sender_tab_id = request.headers.get("X-Tab-ID")

            from hecos.core.commands.executor import get_executor
            executor = get_executor()

            result = executor.execute(
                raw_input=raw_input,
                config=config_manager.config,
                config_manager=config_manager,
                current_user_role=role,
                current_user_id=user_id,
                session_id=session_id,
                sender_tab_id=sender_tab_id,
                page_context=page_context
            )

            # NOTE: Rendering is handled by cmd_execute.js in the frontend (direct DOM injection).
            # We intentionally do NOT fire sm.add_event("system_response") here to avoid
            # double-rendering when the command also goes through the loop.py chat path.

            return jsonify(result)
        except Exception as e:
            _log.error(f"[API Commands] Error running {raw_input}: {e}", exc_info=True)
            return jsonify({"ok": False, "error": str(e)}), 500
