"""
routes_widgets_room.py
─────────────────────────────────────────────────────────────────────────────
Hecos WebUI — Control Room Logic Routes
Handles the unified multi-page dashboard configuration (pages, widget
assignment, visibility, spanning, height, and layout order) shared between
Module A (Chat Control Room) and Module B (Standalone /home Control Room).
─────────────────────────────────────────────────────────────────────────────
"""
import re
import unicodedata
import uuid
from flask import jsonify, request, make_response, render_template
from flask_login import login_required

from .routes_widgets_api import invalidate_widgets_cache

_ICON_RE = re.compile(r"^fa-[a-z0-9-]+$")
_DEFAULT_PAGE_ICON = "fa-layer-group"
_DEFAULT_PAGE_ID = "main"
_DEFAULT_PAGE_NAME = "Main"
_MAX_PAGE_NAME_LEN = 32


def _as_dict(obj):
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return dict(obj)
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "__dict__"):
        return dict(obj.__dict__)
    return {}


def _sanitize_icon(icon) -> str:
    if isinstance(icon, str):
        cleaned = icon.strip()
        if cleaned.startswith("fas "):
            cleaned = cleaned[4:].strip()
        if _ICON_RE.match(cleaned):
            return cleaned
    return _DEFAULT_PAGE_ICON


def _sanitize_name(name) -> str:
    if not isinstance(name, str):
        return ""
    return " ".join(name.strip().split())[:_MAX_PAGE_NAME_LEN]


def _dedup_ids(items) -> list:
    if not isinstance(items, list):
        return []
    seen = set()
    out = []
    for item in items:
        if isinstance(item, str):
            val = item.strip()
            if val and val not in seen:
                seen.add(val)
                out.append(val)
    return out


def _make_page_id(name: str, existing_ids: set) -> str:
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "_", ascii_name.lower()).strip("_")[:24]
    if not slug:
        slug = "page"
    candidate = slug
    idx = 2
    while candidate in existing_ids:
        candidate = f"{slug}_{idx}"
        idx += 1
        if idx > 999:
            candidate = f"page_{uuid.uuid4().hex[:6]}"
            break
    return candidate


def _extract_widget_prefs(cfg: dict, ext_id: str) -> dict:
    raw = cfg.get("widgets", {}).get("per_widget", {}).get(ext_id)
    return _as_dict(raw)


def _enrich_room_widget(w: dict, cfg: dict) -> dict:
    ext_id = w.get("extension_id", "?")
    prefs = _extract_widget_prefs(cfg, ext_id)
    room_span = prefs.get("room_span", prefs.get("sidebar_span", prefs.get("standalone_span", w.get("room_span", 1))))
    if room_span not in (1, 2):
        room_span = 1
    room_height = prefs.get("room_height", prefs.get("sidebar_height", prefs.get("standalone_height", w.get("room_height", None))))
    room_theme = prefs.get("theme", w.get("theme", "default"))
    if hasattr(room_theme, "value"):
        room_theme = room_theme.value
    bg_color = prefs.get("bg_color", w.get("bg_color", ""))
    bg_image = prefs.get("bg_image", w.get("bg_image", ""))
    return {
        **w,
        "room_visible": True,
        "room_span": room_span,
        "room_height": room_height,
        "theme": room_theme or "default",
        "bg_color": bg_color or "",
        "bg_image": bg_image or "",
    }


def _load_or_init_pages(cfg: dict, all_widgets: list, config_manager, _save_config, auto_persist: bool = True) -> list:
    """
    Loads unified Control Room pages from widgets.room_pages.
    Transparently auto-migrates existing single-page room_layout/visible widgets
    into Page 1 ("Main") on first access, and auto-places newly installed
    unconfigured widgets onto Page 1.
    """
    widgets_cfg = cfg.get("widgets", {}) or {}
    raw_pages = widgets_cfg.get("room_pages") or []
    per_widget = widgets_cfg.get("per_widget", {}) or {}

    pages = []
    seen_page_ids = set()
    for rp in raw_pages:
        pd = _as_dict(rp)
        pid = str(pd.get("id") or "").strip()
        pname = _sanitize_name(pd.get("name") or "")
        if not pid or pid in seen_page_ids:
            continue
        if not pname:
            pname = pid.capitalize()
        seen_page_ids.add(pid)
        pages.append({
            "id": pid,
            "name": pname,
            "icon": _sanitize_icon(pd.get("icon")),
            "widgets": _dedup_ids(pd.get("widgets") or []),
        })

    dirty = False

    if not pages:
        # First-time migration from legacy single-page Control Room
        legacy_layout = widgets_cfg.get("room_layout") or widgets_cfg.get("home_layout") or []
        order_map = {eid: i for i, eid in enumerate(legacy_layout)}

        visible_widgets = []
        for w in all_widgets:
            ext_id = w.get("extension_id")
            if not ext_id or not w.get("enabled", True) or not w.get("plugin_active", True):
                continue
            prefs = _extract_widget_prefs(cfg, ext_id)
            room_visible = prefs.get("room_visible", prefs.get("sidebar_visible", w.get("room_visible", False)))
            if room_visible:
                visible_widgets.append(ext_id)

        if order_map:
            visible_widgets.sort(key=lambda eid: order_map.get(eid, 9999))

        pages = [{
            "id": _DEFAULT_PAGE_ID,
            "name": _DEFAULT_PAGE_NAME,
            "icon": _DEFAULT_PAGE_ICON,
            "widgets": _dedup_ids(visible_widgets),
        }]
        dirty = True
    else:
        # Auto-place newly installed HPM widgets that have never been explicitly
        # configured in per_widget and are not yet assigned to any page.
        assigned_ids = {wid for p in pages for wid in p["widgets"]}
        for w in all_widgets:
            ext_id = w.get("extension_id")
            if not ext_id or ext_id in assigned_ids:
                continue
            if not w.get("enabled", True) or not w.get("plugin_active", True):
                continue
            if ext_id not in per_widget and w.get("room_visible", True) and not w.get("visible", False):
                pages[0]["widgets"].append(ext_id)
                assigned_ids.add(ext_id)
                dirty = True

    if dirty and auto_persist and config_manager:
        config_manager.set(pages, "widgets", "room_pages")
        if pages:
            config_manager.set(list(pages[0]["widgets"]), "widgets", "room_layout")
        _save_config()

    return pages


def _persist_pages(pages: list, config_manager, _save_config, affected_widget_ids=None) -> bool:
    """
    Saves room_pages, keeps legacy room_layout in sync with page 0, and
    reconciles per_widget[wid].room_visible (and Sidebar XOR when added).
    """
    res = config_manager.set(pages, "widgets", "room_pages")
    if not res:
        return False

    if pages:
        config_manager.set(list(pages[0]["widgets"]), "widgets", "room_layout")

    if affected_widget_ids:
        all_assigned = {wid for p in pages for wid in p["widgets"]}
        for wid in _dedup_ids(list(affected_widget_ids)):
            in_room = wid in all_assigned
            config_manager.set(in_room, "widgets", "per_widget", wid, "room_visible")
            if in_room:
                config_manager.set(False, "widgets", "per_widget", wid, "visible")

    ok = _save_config()
    invalidate_widgets_cache()
    return bool(ok)


def _serialize_pages(pages: list, active_map: dict) -> list:
    out = []
    for p in pages:
        active_wids = [wid for wid in p["widgets"] if wid in active_map]
        out.append({
            "id": p["id"],
            "name": p["name"],
            "icon": p["icon"],
            "widgets": list(p["widgets"]),
            "active_widgets": active_wids,
            "count": len(active_wids),
        })
    return out


def init_widget_room_routes(app, config_manager, _log, _get_config, _save_config):

    @app.route("/api/widgets/room", methods=["GET"])
    @login_required
    def api_render_room_widgets():
        """
        Returns the unified pages list, resolved active_page_id, ordered widget
        metadata for the active page, and the catalog of all installed widgets.
        Shared identically by Module A (Chat) and Module B (Standalone /home).
        """
        from hecos.core.system.extension_loader import get_all_widgets
        ctx = request.args.get("context", "sidebar")
        requested_page_id = (request.args.get("page_id") or "").strip()

        cfg = _get_config()
        all_widgets = get_all_widgets(config=cfg)
        active_map = {
            w["extension_id"]: w
            for w in all_widgets
            if w.get("extension_id") and w.get("enabled", True) and w.get("plugin_active", True)
        }

        pages = _load_or_init_pages(cfg, all_widgets, config_manager, _save_config, auto_persist=True)

        # Resolve active page
        active_page = next((p for p in pages if p["id"] == requested_page_id), None)
        if active_page is None:
            active_page = pages[0]

        room_widgets = []
        for ext_id in active_page["widgets"]:
            w = active_map.get(ext_id)
            if w:
                room_widgets.append(_enrich_room_widget(w, cfg))

        # Build reverse map: widget -> list of page IDs containing it
        widget_pages_map = {}
        for p in pages:
            for wid in p["widgets"]:
                widget_pages_map.setdefault(wid, []).append(p["id"])

        available_widgets = []
        for ext_id, w in active_map.items():
            available_widgets.append({
                "extension_id": ext_id,
                "display_name": w.get("display_name") or ext_id,
                "description": w.get("description") or "",
                "version": w.get("version") or "1.0",
                "icon": w.get("icon") or "",
                "visible": bool(w.get("visible", False)),
                "room_visible": bool(ext_id in widget_pages_map),
                "pages": widget_pages_map.get(ext_id, []),
            })

        _log.debug(
            f"[ROOM] [{ctx}] page={active_page['id']} returning "
            f"{len(room_widgets)} widgets across {len(pages)} pages"
        )

        resp = jsonify({
            "ok": True,
            "pages": _serialize_pages(pages, active_map),
            "active_page_id": active_page["id"],
            "widgets": room_widgets,
            "available_widgets": available_widgets,
        })
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return resp


    @app.route("/api/widgets/room/pages", methods=["GET"])
    @login_required
    def api_get_room_pages():
        from hecos.core.system.extension_loader import get_all_widgets
        cfg = _get_config()
        all_widgets = get_all_widgets(config=cfg)
        active_map = {
            w["extension_id"]: w
            for w in all_widgets
            if w.get("extension_id") and w.get("enabled", True) and w.get("plugin_active", True)
        }
        pages = _load_or_init_pages(cfg, all_widgets, config_manager, _save_config, auto_persist=True)
        resp = jsonify({"ok": True, "pages": _serialize_pages(pages, active_map)})
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return resp


    @app.route("/api/widgets/room/pages", methods=["POST"])
    @login_required
    def api_create_room_page():
        from hecos.core.system.extension_loader import get_all_widgets
        data = request.get_json(silent=True) or {}
        name = _sanitize_name(data.get("name", ""))
        if not name:
            return jsonify({"ok": False, "error": "Page name is required"}), 400

        icon = _sanitize_icon(data.get("icon"))
        initial_widgets = _dedup_ids(data.get("widgets") or [])

        cfg = _get_config()
        all_widgets = get_all_widgets(config=cfg)
        active_map = {
            w["extension_id"]: w
            for w in all_widgets
            if w.get("extension_id") and w.get("enabled", True) and w.get("plugin_active", True)
        }
        pages = _load_or_init_pages(cfg, all_widgets, config_manager, _save_config, auto_persist=False)

        existing_ids = {p["id"] for p in pages}
        new_page = {
            "id": _make_page_id(name, existing_ids),
            "name": name,
            "icon": icon,
            "widgets": initial_widgets,
        }
        pages.append(new_page)
        _log.info(f"WIDGETS: Creating Control Room page [{new_page['id']}] '{name}' ({icon})")

        if _persist_pages(pages, config_manager, _save_config, affected_widget_ids=initial_widgets):
            return jsonify({
                "ok": True,
                "page": new_page,
                "pages": _serialize_pages(pages, active_map),
            })
        return jsonify({"ok": False, "error": "Failed to save new page"}), 500


    @app.route("/api/widgets/room/pages/reorder", methods=["PATCH"])
    @login_required
    def api_reorder_room_pages():
        from hecos.core.system.extension_loader import get_all_widgets
        data = request.get_json(silent=True) or {}
        order = data.get("order")
        if not isinstance(order, list):
            return jsonify({"ok": False, "error": "'order' must be an array of page IDs"}), 400

        cfg = _get_config()
        all_widgets = get_all_widgets(config=cfg)
        active_map = {
            w["extension_id"]: w
            for w in all_widgets
            if w.get("extension_id") and w.get("enabled", True) and w.get("plugin_active", True)
        }
        pages = _load_or_init_pages(cfg, all_widgets, config_manager, _save_config, auto_persist=False)

        page_map = {p["id"]: p for p in pages}
        reordered = []
        seen = set()
        for pid in order:
            if isinstance(pid, str) and pid in page_map and pid not in seen:
                reordered.append(page_map[pid])
                seen.add(pid)
        for p in pages:
            if p["id"] not in seen:
                reordered.append(p)

        _log.info(f"WIDGETS: Reordering Control Room pages -> {[p['id'] for p in reordered]}")
        if _persist_pages(reordered, config_manager, _save_config):
            return jsonify({"ok": True, "pages": _serialize_pages(reordered, active_map)})
        return jsonify({"ok": False, "error": "Failed to reorder pages"}), 500


    @app.route("/api/widgets/room/pages/<page_id>", methods=["PATCH"])
    @login_required
    def api_update_room_page(page_id):
        from hecos.core.system.extension_loader import get_all_widgets
        data = request.get_json(silent=True) or {}

        cfg = _get_config()
        all_widgets = get_all_widgets(config=cfg)
        active_map = {
            w["extension_id"]: w
            for w in all_widgets
            if w.get("extension_id") and w.get("enabled", True) and w.get("plugin_active", True)
        }
        pages = _load_or_init_pages(cfg, all_widgets, config_manager, _save_config, auto_persist=False)

        target = next((p for p in pages if p["id"] == page_id), None)
        if target is None:
            return jsonify({"ok": False, "error": "Page not found"}), 404

        affected = set()

        if "name" in data:
            new_name = _sanitize_name(data["name"])
            if not new_name:
                return jsonify({"ok": False, "error": "Page name cannot be empty"}), 400
            target["name"] = new_name

        if "icon" in data:
            target["icon"] = _sanitize_icon(data["icon"])

        if "widgets" in data:
            if not isinstance(data["widgets"], list):
                return jsonify({"ok": False, "error": "'widgets' must be a list"}), 400
            old_set = set(target["widgets"])
            new_list = _dedup_ids(data["widgets"])
            affected.update(old_set.symmetric_difference(new_list))
            target["widgets"] = new_list

        if "add_widget" in data and isinstance(data["add_widget"], str):
            wid = data["add_widget"].strip()
            if wid:
                if wid not in target["widgets"]:
                    target["widgets"].append(wid)
                affected.add(wid)

        if "remove_widget" in data and isinstance(data["remove_widget"], str):
            wid = data["remove_widget"].strip()
            if wid:
                target["widgets"] = [w for w in target["widgets"] if w != wid]
                affected.add(wid)

        _log.info(f"WIDGETS: Updated Control Room page [{page_id}] -> name='{target['name']}', widgets={len(target['widgets'])}")
        if _persist_pages(pages, config_manager, _save_config, affected_widget_ids=affected):
            return jsonify({
                "ok": True,
                "page": target,
                "pages": _serialize_pages(pages, active_map),
            })
        return jsonify({"ok": False, "error": "Failed to update page"}), 500


    @app.route("/api/widgets/room/pages/<page_id>/move_widget", methods=["POST"])
    @login_required
    def api_move_widget_between_pages(page_id):
        from hecos.core.system.extension_loader import get_all_widgets
        data = request.get_json(silent=True) or {}
        ext_id = (data.get("ext_id") or "").strip()
        target_page_id = (data.get("target_page_id") or "").strip()
        copy_mode = bool(data.get("copy", False))

        if not ext_id or not target_page_id:
            return jsonify({"ok": False, "error": "'ext_id' and 'target_page_id' are required"}), 400

        cfg = _get_config()
        all_widgets = get_all_widgets(config=cfg)
        active_map = {
            w["extension_id"]: w
            for w in all_widgets
            if w.get("extension_id") and w.get("enabled", True) and w.get("plugin_active", True)
        }
        pages = _load_or_init_pages(cfg, all_widgets, config_manager, _save_config, auto_persist=False)

        src = next((p for p in pages if p["id"] == page_id), None)
        dst = next((p for p in pages if p["id"] == target_page_id), None)
        if src is None or dst is None:
            return jsonify({"ok": False, "error": "Source or target page not found"}), 404

        if not copy_mode and src["id"] != dst["id"]:
            src["widgets"] = [w for w in src["widgets"] if w != ext_id]
        if ext_id not in dst["widgets"]:
            dst["widgets"].append(ext_id)

        action = "Copied" if copy_mode else "Moved"
        _log.info(f"WIDGETS: {action} [{ext_id}] from page [{page_id}] -> [{target_page_id}]")

        if _persist_pages(pages, config_manager, _save_config, affected_widget_ids=[ext_id]):
            return jsonify({"ok": True, "pages": _serialize_pages(pages, active_map)})
        return jsonify({"ok": False, "error": "Failed to move widget"}), 500


    @app.route("/api/widgets/room/pages/<page_id>", methods=["DELETE"])
    @login_required
    def api_delete_room_page(page_id):
        from hecos.core.system.extension_loader import get_all_widgets
        cfg = _get_config()
        all_widgets = get_all_widgets(config=cfg)
        active_map = {
            w["extension_id"]: w
            for w in all_widgets
            if w.get("extension_id") and w.get("enabled", True) and w.get("plugin_active", True)
        }
        pages = _load_or_init_pages(cfg, all_widgets, config_manager, _save_config, auto_persist=False)

        if len(pages) <= 1:
            return jsonify({"ok": False, "error": "Cannot delete the last remaining page"}), 400

        target = next((p for p in pages if p["id"] == page_id), None)
        if target is None:
            return jsonify({"ok": False, "error": "Page not found"}), 404

        move_to_id = (request.args.get("move_widgets_to") or "").strip()
        if not move_to_id:
            body = request.get_json(silent=True) or {}
            move_to_id = (body.get("move_widgets_to") or "").strip()

        removed_widgets = list(target["widgets"])
        remaining = [p for p in pages if p["id"] != page_id]

        if move_to_id:
            dst = next((p for p in remaining if p["id"] == move_to_id), None)
            if dst is not None:
                for wid in removed_widgets:
                    if wid not in dst["widgets"]:
                        dst["widgets"].append(wid)

        _log.info(f"WIDGETS: Deleted Control Room page [{page_id}] ('{target['name']}')")
        if _persist_pages(remaining, config_manager, _save_config, affected_widget_ids=removed_widgets):
            return jsonify({
                "ok": True,
                "pages": _serialize_pages(remaining, active_map),
                "fallback_page_id": remaining[0]["id"],
            })
        return jsonify({"ok": False, "error": "Failed to delete page"}), 500


    @app.route("/api/widgets/room/<ext_id>/frame", methods=["GET"])
    @login_required
    def api_render_room_widget_frame(ext_id):
        """
        Returns the raw HTML document for a specific widget.
        Used as the src for iframes in the Control Room to isolate JS context.
        """
        from hecos.core.system.extension_loader import get_all_widgets
        from hecos.core.i18n.translator import t, get_translator

        cfg = _get_config()
        widgets = get_all_widgets(config=cfg)
        manifest = next((w for w in widgets if w["extension_id"] == ext_id), None)

        if not manifest:
            return "Widget not found", 404

        widget_theme = _extract_widget_prefs(cfg, ext_id).get("theme", "default")
        if hasattr(widget_theme, "value"):
            widget_theme = widget_theme.value

        trans = get_translator().get_translations()

        html = render_template(
            "modules/control_room_widget_frame.html",
            ext_id=ext_id,
            ext_manifest=manifest,
            widget_theme=widget_theme,
            zconfig=cfg,
            translations=trans,
            t=t
        )
        resp = make_response(html)
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return resp


    @app.route("/api/widgets/<ext_id>/room_visible", methods=["POST"])
    @login_required
    def api_set_widget_room_visible(ext_id):
        """
        Updates unified Control Room visibility for a widget.
        - If `page_id` is provided: adds/removes the widget ONLY on that page.
        - If `page_id` is omitted (e.g. Central Hub toggle): adds to Page 1 (if
          not already on any page) when visible=True, or removes from all pages
          when visible=False.
        """
        from hecos.core.system.extension_loader import get_all_widgets
        data = request.get_json(silent=True) or {}
        if "visible" not in data:
            return jsonify({"ok": False, "error": "'visible' field required"}), 400

        visible = bool(data["visible"])
        page_id = (data.get("page_id") or "").strip()

        cfg = _get_config()
        all_widgets = get_all_widgets(config=cfg)
        pages = _load_or_init_pages(cfg, all_widgets, config_manager, _save_config, auto_persist=False)

        if page_id:
            target = next((p for p in pages if p["id"] == page_id), None)
            if target is not None:
                if visible:
                    if ext_id not in target["widgets"]:
                        target["widgets"].append(ext_id)
                else:
                    target["widgets"] = [w for w in target["widgets"] if w != ext_id]
        else:
            if visible:
                already_present = any(ext_id in p["widgets"] for p in pages)
                if not already_present and pages:
                    pages[0]["widgets"].append(ext_id)
            else:
                for p in pages:
                    p["widgets"] = [w for w in p["widgets"] if w != ext_id]

        _log.info(f"WIDGETS: Unified room visibility [{ext_id}] -> {visible} (page={page_id or 'all'})")
        if _persist_pages(pages, config_manager, _save_config, affected_widget_ids=[ext_id]):
            still_in_room = any(ext_id in p["widgets"] for p in pages)
            return jsonify({"ok": True, "ext_id": ext_id, "room_visible": still_in_room})
        return jsonify({"ok": False, "error": "Failed to update config"}), 500


    @app.route("/api/widgets/<ext_id>/room_span", methods=["POST"])
    @login_required
    def api_set_widget_room_span(ext_id):
        data = request.get_json(silent=True) or {}
        span = data.get("span", 1)
        if span not in (1, 2):
            return jsonify({"ok": False, "error": "span must be 1 or 2"}), 400
        _log.info(f"WIDGETS: Unified room span [{ext_id}] -> {span}")
        res = config_manager.set(span, "widgets", "per_widget", ext_id, "room_span")
        if res:
            _save_config()
            invalidate_widgets_cache()
            return jsonify({"ok": True, "ext_id": ext_id, "room_span": span})
        return jsonify({"ok": False, "error": "Failed to update config"}), 500


    @app.route("/api/widgets/<ext_id>/room_height", methods=["POST"])
    @login_required
    def api_set_widget_room_height(ext_id):
        data = request.get_json(silent=True) or {}
        height = data.get("height")  # None is valid (resets to default)
        _log.info(f"WIDGETS: Unified room height [{ext_id}] -> {height}")
        res = config_manager.set(height, "widgets", "per_widget", ext_id, "room_height")
        if res:
            _save_config()
            invalidate_widgets_cache()
            return jsonify({"ok": True, "ext_id": ext_id, "room_height": height})
        return jsonify({"ok": False, "error": "Failed to update config"}), 500


    @app.route("/api/widgets/room/layout", methods=["PATCH"])
    @login_required
    def api_set_room_layout():
        from hecos.core.system.extension_loader import get_all_widgets
        data = request.get_json(silent=True) or {}
        layout = data.get("layout")
        page_id = (data.get("page_id") or "").strip()
        if not isinstance(layout, list):
            return jsonify({"ok": False, "error": "'layout' must be an array of ext_ids"}), 400

        clean_layout = _dedup_ids(layout)
        cfg = _get_config()
        all_widgets = get_all_widgets(config=cfg)
        pages = _load_or_init_pages(cfg, all_widgets, config_manager, _save_config, auto_persist=False)

        target = next((p for p in pages if p["id"] == page_id), None) if page_id else (pages[0] if pages else None)
        if target is not None:
            # Preserve any widgets currently inactive/disabled (not rendered in grid)
            # at the end of the page's widget list so re-enabling keeps them on the page.
            active_ids = {
                w["extension_id"]
                for w in all_widgets
                if w.get("extension_id") and w.get("enabled", True) and w.get("plugin_active", True)
            }
            inactive_tail = [wid for wid in target["widgets"] if wid not in active_ids and wid not in clean_layout]
            target["widgets"] = clean_layout + inactive_tail
            _log.info(f"WIDGETS: Saving unified layout for page [{target['id']}] -> {clean_layout}")
            if _persist_pages(pages, config_manager, _save_config):
                return jsonify({"ok": True, "page_id": target["id"], "layout": clean_layout})
            return jsonify({"ok": False, "error": "Failed to update layout"}), 500

        res = config_manager.set(clean_layout, "widgets", "room_layout")
        if res:
            _save_config()
            return jsonify({"ok": True})
        return jsonify({"ok": False, "error": "Failed to update layout"}), 500
