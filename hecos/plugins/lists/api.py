"""
MODULE: Lists API
DESCRIPTION: Flask REST endpoints for the Lists plugin.
"""

from flask import Blueprint, request, jsonify
from hecos.core.logging import logger

lists_bp = Blueprint("lists", __name__, url_prefix="/api/lists")

def init_plugin_routes(app, cfg_mgr, root_dir, logger):
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


# ── Export ────────────────────────────────────────────────────────────────────

def _list_to_dict(list_id: str) -> dict | None:
    """Returns a full exportable dict for a list (metadata + items)."""
    from hecos.plugins.lists import store
    lst = store.get_list_by_id(list_id)
    if not lst:
        return None
    items = store.get_items(list_id)
    return {
        "name": lst["name"],
        "icon": lst.get("icon", ""),
        "color": lst.get("color", ""),
        "created_at": lst.get("created_at", ""),
        "items": [
            {
                "text": i["text"],
                "status": i["status"],
                "priority": i.get("priority", 0),
                "label": i.get("label", "") or "",
                "created_at": i.get("created_at", "") or "",
                "completed_at": i.get("completed_at", "") or ""
            }
            for i in items
        ]
    }


def _dict_to_yaml(data: dict) -> str:
    """Converts a list dict to YAML string without external dependencies."""
    from hecos.core.system.version import VERSION
    def _scalar(v):
        if v is None:
            return "~"
        s = str(v)
        if any(c in s for c in [':', '#', '[', ']', '{', '}', ',', '&', '*', '!', '|', '>', "'", '"', '%', '@', '`', '\n']):
            return f'"{s.replace(chr(34), chr(92)+chr(34))}"'
        return s or '""'

    lines = [
        f"# List created with Hecos v-{VERSION}",
        f"nome: {_scalar(data['name'])}",
        f"icona: {_scalar(data.get('icon',''))}",
        f"colore: {_scalar(data.get('color',''))}",
        f"creata: {_scalar(data.get('created_at',''))}",
        "elementi:",
    ]
    for item in data.get("items", []):
        lines.append(f"  - testo: {_scalar(item['text'])}")
        lines.append(f"    stato: {_scalar(item['status'])}")
        if item.get("priority", 0):
            lines.append(f"    priorita: {item['priority']}")
        if item.get("label"):
            lines.append(f"    etichetta: {_scalar(item['label'])}")
        if item.get("created_at"):
            lines.append(f"    creato: {_scalar(item['created_at'][:10])}")
        if item.get("completed_at"):
            lines.append(f"    completato: {_scalar(item['completed_at'][:10])}")
    return "\n".join(lines)


def _dict_to_txt(data: dict) -> str:
    """Converts a list dict to readable plain-text format."""
    from hecos.core.system.version import VERSION
    lines = [
        f"# {data['name']}",
        f"# List created with Hecos v-{VERSION}",
        f"# Exported on: {data.get('created_at','')[:10]}",
        ""
    ]
    for item in data.get("items", []):
        mark = "[x]" if item["status"] == "done" else "[ ]"
        suffix = f" [{item['label']}]" if item.get("label") else ""
        priority = "!" * item.get("priority", 0)
        date_parts = []
        if item.get("created_at"):
            date_parts.append(f"created: {item['created_at'][:10]}")
        if item.get("completed_at"):
            date_parts.append(f"done: {item['completed_at'][:10]}")
        date_str = f"  ({', '.join(date_parts)})" if date_parts else ""
        lines.append(f"{mark} {item['text']}{priority}{suffix}{date_str}")
    return "\n".join(lines)


def _dict_to_md(data: dict) -> str:
    """Converts a list dict to standard Markdown checklist format."""
    from hecos.core.system.version import VERSION
    lines = [
        f"# {data['name']}",
        f"*List created with Hecos v-{VERSION}*",
        f"*Exported on: {data.get('created_at','')[:10]}*",
        ""
    ]
    for item in data.get("items", []):
        mark = "- [x]" if item["status"] == "done" else "- [ ]"
        suffix = f" `{item['label']}`" if item.get("label") else ""
        priority = "!" * item.get("priority", 0)
        # Bold priority items
        text = f"**{item['text']}**" if priority else item['text']
        date_parts = []
        if item.get("created_at"):
            date_parts.append(f"created: {item['created_at'][:10]}")
        if item.get("completed_at"):
            date_parts.append(f"done: {item['completed_at'][:10]}")
        date_str = f" *({', '.join(date_parts)})*" if date_parts else ""
        lines.append(f"{mark} {text}{suffix}{date_str}")
    return "\n".join(lines)


@lists_bp.route("/<list_id>/export", methods=["GET"])
def export_list(list_id):
    from flask import Response
    fmt = request.args.get("format", "yaml").lower()
    data = _list_to_dict(list_id)
    if not data:
        return jsonify({"ok": False, "error": "List not found"}), 404

    safe_name = "".join(c for c in data["name"] if c.isalnum() or c in " _-").strip()

    if fmt == "txt":
        content = _dict_to_txt(data)
        mime = "text/plain"
        filename = f"hecos_list_{safe_name}.txt"
    elif fmt == "md":
        content = _dict_to_md(data)
        mime = "text/markdown"
        filename = f"hecos_list_{safe_name}.md"
    else:
        content = _dict_to_yaml(data)
        mime = "text/yaml"
        filename = f"hecos_list_{safe_name}.yaml"

    return Response(
        content,
        mimetype=mime,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@lists_bp.route("/export/all", methods=["GET"])
def export_all_lists():
    from flask import Response
    from hecos.plugins.lists import store
    fmt = request.args.get("format", "yaml").lower()
    lists = store.get_lists(include_archived=False)

    blocks = []
    for lst in lists:
        data = _list_to_dict(lst["id"])
        if data:
            if fmt == "txt":
                blocks.append(_dict_to_txt(data))
            elif fmt == "md":
                blocks.append(_dict_to_md(data))
            else:
                blocks.append(_dict_to_yaml(data))

    separator = "\n\n---\n\n"
    content = separator.join(blocks)
    mime = "text/plain" if fmt == "txt" else ("text/markdown" if fmt == "md" else "text/yaml")
    filename = f"tutte_le_liste.{fmt}"

    return Response(
        content,
        mimetype=mime,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@lists_bp.route("/<list_id>/export/save", methods=["POST"])
def save_export_to_disk(list_id):
    """Saves the exported file to disk in the configured export folder."""
    import os
    from hecos.plugins.lists import store as _store
    from hecos.core.logging import logger as _log

    data_req = request.get_json(force=True) or {}
    fmt = data_req.get("format", "yaml").lower()

    # Resolve export folder: from config or request body
    folder = data_req.get("folder")
    if not folder:
        try:
            from app.config import ConfigManager
            cfg = ConfigManager()
            folder = cfg.config.get("plugins", {}).get("LISTS", {}).get("export_folder", "")
        except Exception:
            folder = ""
    if not folder:
        folder = os.path.join(os.path.expanduser("~"), "Desktop")

    folder = os.path.expandvars(os.path.expanduser(folder))
    os.makedirs(folder, exist_ok=True)

    list_data = _list_to_dict(list_id)
    if not list_data:
        return jsonify({"ok": False, "error": "List not found"}), 404

    safe_name = "".join(c for c in list_data["name"] if c.isalnum() or c in " _-").strip()
    if fmt == "txt":
        content  = _dict_to_txt(list_data)
        filename = f"hecos_list_{safe_name}.txt"
    elif fmt == "md":
        content  = _dict_to_md(list_data)
        filename = f"hecos_list_{safe_name}.md"
    else:
        content  = _dict_to_yaml(list_data)
        filename = f"hecos_list_{safe_name}.yaml"

    filepath = os.path.join(folder, filename)
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        _log.info(f"[LISTS] Exported '{list_data['name']}' to {filepath}")
        return jsonify({"ok": True, "path": filepath, "filename": filename})
    except Exception as e:
        _log.error(f"[LISTS] Export save error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


# ── Import ────────────────────────────────────────────────────────────────────

def _parse_yaml_import(text: str) -> list:
    """
    Parses a simple YAML export (our own format, no dependencies needed).
    Returns a list of list-dicts.
    """
    results = []
    blocks = [b.strip() for b in text.split("---") if b.strip()]
    for block in blocks:
        current = {"name": "", "items": []}
        current_item = None
        for raw_line in block.splitlines():
            line = raw_line.rstrip()
            stripped = line.lstrip()
            if not stripped or stripped.startswith("#"):
                continue

            if line.startswith("nome:"):
                current["name"] = line.split(":", 1)[1].strip().strip('"').strip("'")
            elif line.startswith("icona:"):
                current["icon"] = line.split(":", 1)[1].strip().strip('"').strip("'")
            elif line.startswith("  - testo:"):
                if current_item:
                    current["items"].append(current_item)
                current_item = {
                    "text": line.split(":", 1)[1].strip().strip('"').strip("'"),
                    "status": "pending",
                    "priority": 0,
                    "label": ""
                }
            elif line.startswith("    stato:") and current_item:
                current_item["status"] = line.split(":", 1)[1].strip().strip('"').strip("'")
            elif line.startswith("    priorita:") and current_item:
                try:
                    current_item["priority"] = int(line.split(":", 1)[1].strip())
                except ValueError:
                    pass
            elif line.startswith("    etichetta:") and current_item:
                current_item["label"] = line.split(":", 1)[1].strip().strip('"').strip("'")
            elif line.startswith("    creato:") and current_item:
                current_item["created_at"] = line.split(":", 1)[1].strip().strip('"').strip("'")
            elif line.startswith("    completato:") and current_item:
                current_item["completed_at"] = line.split(":", 1)[1].strip().strip('"').strip("'")
        if current_item:
            current["items"].append(current_item)
        if current["name"]:
            results.append(current)
    return results


def _parse_txt_import(text: str) -> list:
    """
    Parses plain text / markdown checklist formats.
    Supports: [ ]/[x], - [ ]/- [x], * [ ]/- [x]
    Multiple lists separated by ======== or a line starting with '# '
    """
    import re
    results = []
    current = {"name": "", "items": []}

    heading_re  = re.compile(r'^#{1,3}\s+(.+)$')
    check_re    = re.compile(r'^[\-\*]?\s*\[([xX ])\]\s*(.+)$')
    plain_re    = re.compile(r'^\-\s+(.+)$')   # plain "- item" with no checkbox

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        h_match = heading_re.match(line)
        if h_match:
            if current["name"] and current["items"]:
                results.append(current)
            current = {"name": h_match.group(1).strip(), "items": []}
            continue

        c_match = check_re.match(line)
        if c_match:
            done = c_match.group(1).lower() == 'x'
            text_raw = c_match.group(2).strip()
            # extract label like [label] at end
            label_m = re.search(r'\[([^\]]+)\]\s*$', text_raw)
            label = label_m.group(1) if label_m else ""
            if label_m:
                text_raw = text_raw[:label_m.start()].strip()
            current["items"].append({
                "text": text_raw,
                "status": "done" if done else "pending",
                "priority": 0,
                "label": label
            })
            continue

        p_match = plain_re.match(line)
        if p_match and not line.startswith("["):
            current["items"].append({
                "text": p_match.group(1).strip(),
                "status": "pending",
                "priority": 0,
                "label": ""
            })
            continue

    if current["name"] and current["items"]:
        results.append(current)
    elif current["items"] and not current["name"]:
        current["name"] = "Lista importata"
        results.append(current)

    return results


@lists_bp.route("/import", methods=["POST"])
def import_lists():
    """
    Accepts either a file upload (multipart) or JSON body with 'content' and 'format'.
    Formats: yaml, txt, md (markdown).
    Creates all parsed lists in the database.
    """
    from hecos.plugins.lists import store

    content = ""
    fmt = "yaml"

    if request.content_type and "multipart" in request.content_type:
        f = request.files.get("file")
        if not f:
            return jsonify({"ok": False, "error": "No file uploaded"}), 400
        content = f.read().decode("utf-8", errors="replace")
        fname = f.filename or ""
        fmt = "txt" if fname.endswith(".txt") else ("md" if fname.endswith(".md") else "yaml")
    else:
        data_req = request.get_json(force=True) or {}
        content = data_req.get("content", "")
        fmt = data_req.get("format", "yaml").lower()

    if not content.strip():
        return jsonify({"ok": False, "error": "Empty content"}), 400

    # Parse
    try:
        if fmt == "yaml":
            parsed_lists = _parse_yaml_import(content)
        else:  # txt or md
            parsed_lists = _parse_txt_import(content)
    except Exception as e:
        return jsonify({"ok": False, "error": f"Parse error: {e}"}), 400

    if not parsed_lists:
        return jsonify({"ok": False, "error": "No lists found in content"}), 400

    # Save to DB
    created = []
    for pl in parsed_lists:
        lst = store.create_list(
            name=pl.get("name", "Lista importata"),
            icon=pl.get("icon", '<i class="fas fa-list-check"></i>'),
            color=pl.get("color") or None
        )
        if lst:
            for item in pl.get("items", []):
                store.add_item(
                    lst["id"],
                    text=item.get("text", ""),
                    priority=int(item.get("priority", 0)),
                    label=item.get("label") or None
                )
                if item.get("status") == "done":
                    from hecos.plugins.lists import store as _s
                    items = _s.get_items(lst["id"])
                    last = next((i for i in items if i["text"] == item["text"]), None)
                    if last:
                        _s.update_item(last["id"], status="done")
            created.append({"id": lst["id"], "name": lst["name"]})

    return jsonify({"ok": True, "created": created, "count": len(created)}), 201


# ── Backup / Restore ──────────────────────────────────────────────────────────

@lists_bp.route("/backup", methods=["GET"])
def backup_lists():
    """
    Returns a full JSON backup of all lists (including archived ones).
    Format: { ok, count, exported_at, lists: [...] }
    """
    from hecos.plugins.lists import store
    from datetime import datetime, timezone
    try:
        all_lists = store.get_lists(include_archived=True)
        payload = []
        for lst in all_lists:
            d = _list_to_dict(lst["id"])
            if d:
                d["id"] = lst["id"]
                d["archived"] = lst.get("archived", False)
                payload.append(d)
        return jsonify({
            "ok": True,
            "count": len(payload),
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "lists": payload
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@lists_bp.route("/restore", methods=["POST"])
def restore_lists():
    """
    Restores lists from a JSON backup.
    mode=duplicate (default): always creates new lists, preserving existing ones.
    mode=replace: deletes all existing lists first, then recreates.
    Body: { lists: [...], mode: 'duplicate'|'replace' }
    """
    from hecos.plugins.lists import store
    data_req = request.get_json(force=True) or {}
    lists_data = data_req.get("lists", [])
    mode = data_req.get("mode", "duplicate")

    if not lists_data:
        return jsonify({"ok": False, "error": "No lists data provided"}), 400

    try:
        if mode == "replace":
            existing = store.get_lists(include_archived=True)
            for lst in existing:
                store.delete_list(lst["id"])

        created = []
        for pl in lists_data:
            lst = store.create_list(
                name=pl.get("name", "Lista ripristinata"),
                icon=pl.get("icon", "📋"),
                color=pl.get("color") or None
            )
            if lst:
                for item in pl.get("items", []):
                    store.add_item(
                        lst["id"],
                        text=item.get("text", ""),
                        priority=int(item.get("priority", 0)),
                        label=item.get("label") or None
                    )
                    if item.get("status") == "done":
                        items = store.get_items(lst["id"])
                        last = next((i for i in items if i["text"] == item["text"]), None)
                        if last:
                            store.update_item(last["id"], status="done")
                created.append({"id": lst["id"], "name": lst["name"]})

        return jsonify({"ok": True, "restored_count": len(created), "lists": created}), 201
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
