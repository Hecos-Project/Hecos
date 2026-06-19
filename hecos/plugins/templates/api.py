"""
MODULE: Templates API
DESCRIPTION: Flask REST blueprint for template CRUD, rendering and version management.
             Registered at startup via register_routes(app).

Endpoints
─────────
  GET    /api/templates/                    list all templates (optional ?channel= filter)
  GET    /api/templates/<id>                single template with full version history
  POST   /api/templates/                    create template
  PUT    /api/templates/<id>                update template
  DELETE /api/templates/<id>               delete template
  POST   /api/templates/<id>/render         render template (interpolate variables)
  GET    /api/templates/<id>/history        version history (most recent first)
  POST   /api/templates/<id>/restore/<idx>  restore a specific version
"""

from flask import Blueprint, request, jsonify
from hecos.core.logging import logger

templates_bp = Blueprint("templates", __name__, url_prefix="/api/templates")


# ── Blueprint Registration ──────────────────────────────────────────────────────

def register_routes(app) -> None:
    """Register the templates blueprint on the Flask app (idempotent)."""
    if "templates" not in app.blueprints:
        app.register_blueprint(templates_bp)
        logger.debug("TEMPLATES", "API blueprint registered at /api/templates")


# ── Store import helper ────────────────────────────────────────────────────────

def _store():
    """Lazy import of the store module to avoid circular imports at startup."""
    from hecos.plugins.templates import store
    return store


# ── List ───────────────────────────────────────────────────────────────────────

@templates_bp.route("/", methods=["GET"])
def list_templates():
    """
    List all templates.
    Query params:
      channel: optional filter ('email', 'whatsapp', 'telegram', 'discord')
    """
    channel = request.args.get("channel", "").strip() or None
    try:
        items = _store().list_templates(channel=channel)
        return jsonify({"ok": True, "templates": items, "count": len(items)})
    except Exception as e:
        logger.error("TEMPLATES API", f"list error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


# ── Export & Import ────────────────────────────────────────────────────────────

@templates_bp.route("/export", methods=["GET"])
def export_templates():
    """
    Export all templates as a JSON file.
    """
    try:
        items = _store().list_templates()
        return jsonify({"version": 1, "templates": items, "count": len(items)})
    except Exception as e:
        logger.error("TEMPLATES API", f"export error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


@templates_bp.route("/import", methods=["POST"])
def import_templates_route():
    """
    Import templates from a JSON payload.
    Query params:
      mode: 'restore' (default) or 'duplicate'
    """
    mode = request.args.get("mode", "restore")
    data = request.get_json(force=True) or {}
    templates = data.get("templates", [])
    
    if not templates:
        return jsonify({"ok": False, "error": "No templates array found in payload"}), 400
        
    try:
        count = _store().import_templates(templates, mode=mode)
        return jsonify({"ok": True, "imported_count": count})
    except Exception as e:
        logger.error("TEMPLATES API", f"import error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


# ── Get single ─────────────────────────────────────────────────────────────────

@templates_bp.route("/<template_id>", methods=["GET"])
def get_template(template_id: str):
    """Return a single template by ID, including its full version history."""
    try:
        tpl = _store().get_template(template_id)
        if tpl is None:
            return jsonify({"ok": False, "error": "Template not found"}), 404
        return jsonify({"ok": True, "template": tpl})
    except Exception as e:
        logger.error("TEMPLATES API", f"get error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


# ── Create ─────────────────────────────────────────────────────────────────────

@templates_bp.route("/", methods=["POST"])
def create_template():
    """
    Create a new template.
    Required body fields: name (str), channel (str)
    Optional: subject, body_html, body_text, description, tags
    """
    data = request.get_json(force=True) or {}
    try:
        tpl = _store().save_template(data)
        return jsonify({"ok": True, "template": tpl}), 201
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception as e:
        logger.error("TEMPLATES API", f"create error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


# ── Update ─────────────────────────────────────────────────────────────────────

@templates_bp.route("/<template_id>", methods=["PUT"])
def update_template(template_id: str):
    """
    Update an existing template (triggers a version snapshot before saving).
    """
    data = request.get_json(force=True) or {}
    data["id"] = template_id   # ensure upsert targets the correct record
    try:
        tpl = _store().save_template(data)
        return jsonify({"ok": True, "template": tpl})
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception as e:
        logger.error("TEMPLATES API", f"update error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


# ── Delete ─────────────────────────────────────────────────────────────────────

@templates_bp.route("/<template_id>", methods=["DELETE"])
def delete_template(template_id: str):
    """Permanently delete a template."""
    try:
        ok = _store().delete_template(template_id)
        if not ok:
            return jsonify({"ok": False, "error": "Template not found"}), 404
        return jsonify({"ok": True})
    except Exception as e:
        logger.error("TEMPLATES API", f"delete error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


# ── Render ─────────────────────────────────────────────────────────────────────

@templates_bp.route("/<template_id>/render", methods=["POST"])
def render_template(template_id: str):
    """
    Interpolate variables into a template and return the ready content.
    Body: { "variables": { "nome": "Mario", "prodotto": "Hecos" } }
    Returns: { subject, body_html, body_text }
    """
    data      = request.get_json(force=True) or {}
    variables = data.get("variables", {})
    try:
        rendered = _store().render_template(template_id, variables)
        return jsonify({"ok": True, "rendered": rendered})
    except KeyError as e:
        return jsonify({"ok": False, "error": str(e)}), 404
    except Exception as e:
        logger.error("TEMPLATES API", f"render error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


# ── Version History ────────────────────────────────────────────────────────────

@templates_bp.route("/<template_id>/history", methods=["GET"])
def get_history(template_id: str):
    """Return the full version history for a template (most recent first)."""
    try:
        history = _store().get_version_history(template_id)
        return jsonify({"ok": True, "history": history, "count": len(history)})
    except KeyError as e:
        return jsonify({"ok": False, "error": str(e)}), 404
    except Exception as e:
        logger.error("TEMPLATES API", f"history error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


# ── Restore Version ────────────────────────────────────────────────────────────

@templates_bp.route("/<template_id>/restore/<int:version_index>", methods=["POST"])
def restore_version(template_id: str, version_index: int):
    """
    Restore a template to a specific historical version.
    version_index: 0 = most recent snapshot, 1 = one before that, etc.
    The current state is automatically saved as a new snapshot before restoring.
    """
    try:
        tpl = _store().restore_version(template_id, version_index)
        return jsonify({"ok": True, "template": tpl})
    except KeyError as e:
        return jsonify({"ok": False, "error": str(e)}), 404
    except IndexError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception as e:
        logger.error("TEMPLATES API", f"restore error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500
