"""
MODULE: Lists API
DESCRIPTION: Flask REST endpoints for the Lists plugin.
"""

from flask import Blueprint, request, jsonify
from hecos.core.logging import logger

lists_bp = Blueprint("lists", __name__, url_prefix="/api/lists")

def register_routes(app):
    """Registers the lists blueprint on the Flask app (idempotent)."""
    if "lists" not in app.blueprints:
        app.register_blueprint(lists_bp)
        logger.debug("LISTS", "API blueprint registered at /api/lists")

# ── Lists CRUD ────────────────────────────────────────────────────────────────

@lists_bp.route("", methods=["GET"])
def get_all_lists():
    from hecos.plugins.lists import store
    include_archived = request.args.get("archived", "false").lower() == "true"
    try:
        lists = store.get_lists(include_archived=include_archived)
        return jsonify({"ok": True, "lists": lists})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@lists_bp.route("", methods=["POST"])
def create_new_list():
    from hecos.plugins.lists import store
    data = request.get_json(force=True) or {}
    name = data.get("name")
    if not name:
        return jsonify({"ok": False, "error": "name is required"}), 400
    
    icon = data.get("icon", "📋")
    color = data.get("color")
    try:
        lst = store.create_list(name, icon, color)
        if lst:
            return jsonify({"ok": True, "list": lst}), 201
        return jsonify({"ok": False, "error": "Database error"}), 500
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@lists_bp.route("/<list_id>", methods=["GET"])
def get_single_list(list_id):
    from hecos.plugins.lists import store
    lst = store.get_list_by_id(list_id)
    if not lst:
        return jsonify({"ok": False, "error": "List not found"}), 404
    return jsonify({"ok": True, "list": lst})

@lists_bp.route("/<list_id>", methods=["PATCH", "PUT"])
def patch_list(list_id):
    from hecos.plugins.lists import store
    data = request.get_json(force=True) or {}
    try:
        updated = store.update_list(list_id, **data)
        if updated:
            return jsonify({"ok": True, "list": store.get_list_by_id(list_id)})
        return jsonify({"ok": False, "error": "List not found or invalid fields"}), 404
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@lists_bp.route("/<list_id>", methods=["DELETE"])
def remove_list(list_id):
    from hecos.plugins.lists import store
    deleted = store.delete_list(list_id)
    if deleted:
        return jsonify({"ok": True})
    return jsonify({"ok": False, "error": "List not found"}), 404

# ── List Items CRUD ────────────────────────────────────────────────────────────

@lists_bp.route("/<list_id>/items", methods=["GET"])
def get_list_items(list_id):
    from hecos.plugins.lists import store
    status = request.args.get("status")
    try:
        items = store.get_items(list_id, status_filter=status)
        return jsonify({"ok": True, "items": items})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@lists_bp.route("/<list_id>/items", methods=["POST"])
def add_new_item(list_id):
    from hecos.plugins.lists import store
    data = request.get_json(force=True) or {}
    text = data.get("text")
    if not text:
        return jsonify({"ok": False, "error": "text is required"}), 400
    
    priority = int(data.get("priority", 0))
    label = data.get("label")
    try:
        item = store.add_item(list_id, text, priority, label)
        if item:
            return jsonify({"ok": True, "item": item}), 201
        return jsonify({"ok": False, "error": "Failed to add item"}), 500
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@lists_bp.route("/items/<item_id>", methods=["PATCH", "PUT"])
def patch_item(item_id):
    from hecos.plugins.lists import store
    data = request.get_json(force=True) or {}
    try:
        updated = store.update_item(item_id, **data)
        if updated:
            return jsonify({"ok": True})
        return jsonify({"ok": False, "error": "Item not found"}), 404
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@lists_bp.route("/items/<item_id>", methods=["DELETE"])
def remove_item(item_id):
    from hecos.plugins.lists import store
    deleted = store.delete_item(item_id)
    if deleted:
        return jsonify({"ok": True})
    return jsonify({"ok": False, "error": "Item not found"}), 404

@lists_bp.route("/<list_id>/clear_done", methods=["POST"])
def clear_done(list_id):
    from hecos.plugins.lists import store
    try:
        count = store.clear_done_items(list_id)
        return jsonify({"ok": True, "deleted_count": count})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@lists_bp.route("/<list_id>/reorder", methods=["POST"])
def reorder_list(list_id):
    from hecos.plugins.lists import store
    data = request.get_json(force=True) or {}
    ordered_ids = data.get("ordered_ids", [])
    if not ordered_ids:
        return jsonify({"ok": False, "error": "ordered_ids array is required"}), 400
    
    try:
        store.reorder_items(list_id, ordered_ids)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# ── Categories ────────────────────────────────────────────────────────────────

@lists_bp.route("/categories", methods=["GET"])
def get_cats():
    from hecos.plugins.lists import store
    try:
        cats = store.get_categories()
        return jsonify({"ok": True, "categories": cats})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@lists_bp.route("/categories/<cat_id>", methods=["DELETE"])
def remove_cat(cat_id):
    from hecos.plugins.lists import store
    try:
        if store.delete_category(cat_id):
            return jsonify({"ok": True})
        return jsonify({"ok": False, "error": "Category not found"}), 404
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
