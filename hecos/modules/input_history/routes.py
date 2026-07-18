"""
routes.py
API endpoints for WebUI to interact with Input History.
"""
from flask import Blueprint, request, jsonify
from . import history_mgr

input_history_bp = Blueprint('input_history', __name__)

@input_history_bp.route("/api/input-history", methods=["GET"])
def get_history():
    from flask_login import current_user
    uid = current_user.username if current_user.is_authenticated else "admin"
    limit = int(request.args.get("limit", 50))
    entries = history_mgr.get_all(user=uid, limit=limit)
    return jsonify({"ok": True, "entries": entries})

@input_history_bp.route("/api/input-history/push", methods=["POST"])
def push_history():
    from flask_login import current_user
    uid = current_user.username if current_user.is_authenticated else "admin"
    data = request.get_json(silent=True) or {}
    message = data.get("message", "").strip()
    if message:
        history_mgr.push(message, user=uid)
    return jsonify({"ok": True})

@input_history_bp.route("/api/input-history/clear", methods=["POST"])
def clear_history():
    from flask_login import current_user
    uid = current_user.username if current_user.is_authenticated else "admin"
    history_mgr.clear(user=uid)
    return jsonify({"ok": True})
