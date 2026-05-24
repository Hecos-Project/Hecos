"""
MODULE: Contacts API
DESCRIPTION: Flask REST endpoints for the Contacts plugin.
             Registered at boot via on_load() in main.py.

Endpoints:
    GET    /api/contacts                    list / search
    POST   /api/contacts                    create
    GET    /api/contacts/<id>               single contact + fields
    PUT    /api/contacts/<id>               update
    DELETE /api/contacts/<id>               delete
    POST   /api/contacts/<id>/fields        add multi-value field
    DELETE /api/contacts/<id>/fields/<fid>  remove field
    GET    /api/contacts/<id>/export.vcf    export vCard
    POST   /api/contacts/import             import .vcf
    GET    /api/contacts/birthdays          contacts with upcoming birthdays
"""

from flask import Blueprint, request, jsonify, Response, send_file
from hecos.core.logging import logger
import os, pathlib, uuid as _uuid

contacts_bp = Blueprint("contacts", __name__, url_prefix="/api/contacts")


def register_routes(app):
    """Registers the contacts blueprint on the Flask app (idempotent)."""
    if "contacts" not in app.blueprints:
        app.register_blueprint(contacts_bp)
        logger.debug("CONTACTS", "API blueprint registered at /api/contacts")


# ── Contact CRUD ───────────────────────────────────────────────────────────────

@contacts_bp.route("", methods=["GET"])
def list_contacts():
    from hecos.plugins.contacts import store
    q     = request.args.get("q")
    tag   = request.args.get("tag")
    limit = int(request.args.get("limit", 100))
    try:
        if q:
            contacts = store.search(q)
        else:
            contacts = store.list_all(tag=tag, limit=limit)
        return jsonify({"ok": True, "contacts": contacts, "count": len(contacts)})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@contacts_bp.route("", methods=["POST"])
def create_contact():
    from hecos.plugins.contacts import store
    data = request.get_json(force=True) or {}
    try:
        first = data.get("first_name", "")
        if not first:
            return jsonify({"ok": False, "error": "first_name is required"}), 400
        c = store.add(
            first_name=first,
            last_name=data.get("last_name"),
            display_name=data.get("display_name"),
            company=data.get("company"),
            role=data.get("role"),
            birthday=data.get("birthday"),
            address=data.get("address"),
            notes=data.get("notes"),
            label_color=data.get("label_color"),
            tags=data.get("tags"),
        )
        # Add phone/email fields if provided
        for ph in data.get("phones", []):
            store.add_field(c["id"], "phone", ph["value"], label=ph.get("label", "mobile"),
                            is_primary=ph.get("is_primary", False))
        for em in data.get("emails", []):
            store.add_field(c["id"], "email", em["value"], label=em.get("label", "personal"),
                            is_primary=em.get("is_primary", False))
        for soc in data.get("socials", []):
            store.add_field(c["id"], soc["type"], soc["value"], label=soc.get("label"))
        return jsonify({"ok": True, "contact": store.get_by_id(c["id"])}), 201
    except Exception as e:
        logger.debug("CONTACTS", f"POST /api/contacts error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


@contacts_bp.route("/<contact_id>", methods=["GET"])
def get_contact(contact_id):
    from hecos.plugins.contacts import store
    c = store.get_by_id(contact_id)
    if not c:
        return jsonify({"ok": False, "error": "Contact not found"}), 404
    return jsonify({"ok": True, "contact": c})


@contacts_bp.route("/<contact_id>", methods=["PUT"])
def update_contact(contact_id):
    from hecos.plugins.contacts import store
    data = request.get_json(force=True) or {}
    allowed = {"display_name", "first_name", "last_name", "company", "role",
               "birthday", "address", "notes", "label_color", "tags", "photo_path"}
    fields = {k: v for k, v in data.items() if k in allowed}
    try:
        updated = store.update(contact_id, **fields)

        # Sync multi-value fields if present in payload
        if any(k in data for k in ["phones", "emails", "socials"]):
            c = store.get_by_id(contact_id)
            if c:
                # remove existing fields of these types
                for f in c.get("fields", []):
                    ft = f["field_type"]
                    if ("phones" in data and ft == "phone") or \
                       ("emails" in data and ft == "email") or \
                       ("socials" in data and ft not in ["phone", "email"]):
                        store.remove_field(f["id"])
                
                # add new fields
                if "phones" in data:
                    for ph in data["phones"]:
                        if ph.get("value"):
                            store.add_field(contact_id, "phone", ph["value"], label=ph.get("label", "mobile"), is_primary=ph.get("is_primary", False))
                if "emails" in data:
                    for em in data["emails"]:
                        if em.get("value"):
                            store.add_field(contact_id, "email", em["value"], label=em.get("label", "personal"), is_primary=em.get("is_primary", False))
                if "socials" in data:
                    for soc in data["socials"]:
                        if soc.get("type") and soc.get("value"):
                            store.add_field(contact_id, soc["type"], soc["value"], label=soc.get("label"))
                            
            updated = True # Ensure we return success if only fields changed

        if updated:
            return jsonify({"ok": True, "contact": store.get_by_id(contact_id)})
        return jsonify({"ok": False, "error": "Contact not found or no changes"}), 404
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@contacts_bp.route("/<contact_id>", methods=["DELETE"])
def delete_contact(contact_id):
    from hecos.plugins.contacts import store
    deleted = store.delete(contact_id)
    if deleted:
        return jsonify({"ok": True})
    return jsonify({"ok": False, "error": "Contact not found"}), 404



# ── Photo Upload ───────────────────────────────────────────────────────────────

_PHOTOS_DIR = pathlib.Path(__file__).parent.parent.parent / "memory" / "contact_photos"
_ALLOWED_EXT = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.avif'}


@contacts_bp.route("/<contact_id>/photo", methods=["POST"])
def upload_photo(contact_id):
    from hecos.plugins.contacts import store
    c = store.get_by_id(contact_id)
    if not c:
        return jsonify({"ok": False, "error": "Contact not found"}), 404

    if "photo" not in request.files:
        return jsonify({"ok": False, "error": "No file uploaded (field: 'photo')"}), 400

    f   = request.files["photo"]
    ext = pathlib.Path(f.filename).suffix.lower()
    if ext not in _ALLOWED_EXT:
        return jsonify({"ok": False, "error": f"Unsupported image format: {ext}"}), 400

    _PHOTOS_DIR.mkdir(parents=True, exist_ok=True)

    # Remove old photo if present
    old = c.get("photo_path")
    if old:
        old_path = _PHOTOS_DIR / pathlib.Path(old).name
        try:
            old_path.unlink(missing_ok=True)
        except Exception:
            pass

    filename = f"{contact_id}{ext}"
    dest     = _PHOTOS_DIR / filename
    f.save(str(dest))

    photo_url = f"/api/contacts/{contact_id}/photo"
    store.update(contact_id, photo_path=filename, photo_url=photo_url)
    return jsonify({"ok": True, "photo_url": photo_url})


@contacts_bp.route("/<contact_id>/photo", methods=["GET"])
def get_photo(contact_id):
    from hecos.plugins.contacts import store
    c = store.get_by_id(contact_id)
    if not c or not c.get("photo_path"):
        return jsonify({"ok": False, "error": "No photo"}), 404
    path = _PHOTOS_DIR / pathlib.Path(c["photo_path"]).name
    if not path.exists():
        return jsonify({"ok": False, "error": "File missing"}), 404
    return send_file(str(path))


# ── Multi-value Fields ─────────────────────────────────────────────────────────

@contacts_bp.route("/<contact_id>/fields", methods=["POST"])
def add_field(contact_id):
    from hecos.plugins.contacts import store
    data = request.get_json(force=True) or {}
    ft  = data.get("field_type")
    val = data.get("value")
    if not ft or not val:
        return jsonify({"ok": False, "error": "field_type and value are required"}), 400
    try:
        f = store.add_field(contact_id, ft, val,
                            label=data.get("label"),
                            is_primary=data.get("is_primary", False))
        return jsonify({"ok": True, "field": f}), 201
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@contacts_bp.route("/<contact_id>/fields/<field_id>", methods=["DELETE"])
def remove_field(contact_id, field_id):
    from hecos.plugins.contacts import store
    removed = store.remove_field(field_id)
    if removed:
        return jsonify({"ok": True})
    return jsonify({"ok": False, "error": "Field not found"}), 404


# ── vCard ──────────────────────────────────────────────────────────────────────

@contacts_bp.route("/<contact_id>/export.vcf", methods=["GET"])
def export_vcard(contact_id):
    from hecos.plugins.contacts import store
    vcf = store.export_vcard(contact_id)
    if not vcf:
        return jsonify({"ok": False, "error": "Contact not found"}), 404
    c = store.get_by_id(contact_id)
    filename = f"{c.get('display_name','contact').replace(' ','_')}.vcf"
    return Response(
        vcf,
        mimetype="text/vcard",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@contacts_bp.route("/import", methods=["POST"])
def import_vcard():
    from hecos.plugins.contacts import store
    try:
        if "file" in request.files:
            raw = request.files["file"].read().decode("utf-8", errors="replace")
        else:
            raw = (request.get_data(as_text=True) or
                   (request.get_json(force=True) or {}).get("vcf", ""))
        if not raw:
            return jsonify({"ok": False, "error": "No vCard data provided"}), 400
        created = store.import_vcard(raw)
        return jsonify({"ok": True, "imported": len(created), "contacts": created}), 201
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ── Birthday helper ────────────────────────────────────────────────────────────

@contacts_bp.route("/birthdays", methods=["GET"])
def birthdays():
    from hecos.plugins.contacts import store
    days = int(request.args.get("days", 7))
    try:
        today  = store.get_birthdays_today()
        upcoming = store.get_birthdays_upcoming(days)
        return jsonify({"ok": True, "today": today, "upcoming": upcoming})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
