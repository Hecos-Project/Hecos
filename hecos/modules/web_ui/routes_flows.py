"""
Hecos Flows — WebUI Routes
============================
Flask blueprint providing REST API and SSE endpoints for the Flows module.

Endpoints:
  GET  /flows                      → Flows page (flows.html)
  GET  /api/flows/list             → List all flows (JSON)
  GET  /api/flows/<id>             → Get single flow YAML (JSON)
  POST /api/flows/save             → Save/create a flow
  DELETE /api/flows/<id>           → Delete a flow
  POST /api/flows/<id>/run         → Execute a flow immediately
  POST /api/flows/<id>/enable      → Enable flow
  POST /api/flows/<id>/disable     → Disable flow
  POST /api/flows/compile          → NLP → YAML compiler
  GET  /api/flows/<id>/log/stream  → SSE execution log
  GET  /api/flows/actions/catalog  → Available actions catalog
  POST /api/flows/validate         → Validate a YAML string
"""

import logging
import time
import json
from typing import Callable

log = logging.getLogger("HecosFlows.Routes")


def init_flows_routes(app, cfg_mgr, logger=None):
    """Register all /flows routes on the Flask app."""
    _log = logger or log

    from flask import render_template, jsonify, request, Response, stream_with_context
    from flask_login import login_required

    # ── Page ──────────────────────────────────────────────────────────────────

    @app.route("/flows")
    @login_required
    def flows_page():
        from hecos.core.i18n.translator import get_translator
        zconfig_data = cfg_mgr.reload()
        translations = get_translator().get_translations()
        return render_template("flows.html", zconfig=zconfig_data, translations=translations)

    # ── REST API ───────────────────────────────────────────────────────────────

    @app.route("/api/flows/list", methods=["GET"])
    @login_required
    def api_flows_list():
        try:
            from hecos.modules.flows.storage import list_flows
            return jsonify({"ok": True, "flows": list_flows()})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/flows/<flow_id>", methods=["GET"])
    @login_required
    def api_flows_get(flow_id):
        try:
            from hecos.modules.flows.storage import get_flow, get_flow_yaml
            data   = get_flow(flow_id)
            yaml_t = get_flow_yaml(flow_id)
            if data is None:
                return jsonify({"ok": False, "error": f"Flow '{flow_id}' not found."}), 404
            return jsonify({"ok": True, "flow": data, "yaml": yaml_t})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/flows/save", methods=["POST"])
    @login_required
    def api_flows_save():
        try:
            payload = request.get_json(force=True)
            yaml_text = payload.get("yaml", "")
            if not yaml_text.strip():
                return jsonify({"ok": False, "error": "Empty YAML."}), 400

            from hecos.modules.flows.validator import validate_yaml_string
            from hecos.modules.flows.storage import save_flow
            from hecos.modules.flows.engine import schedule_flow

            is_valid, errors, flow_dict = validate_yaml_string(yaml_text)
            if not is_valid:
                return jsonify({"ok": False, "errors": errors}), 422

            flow_id = save_flow(flow_dict, raw_yaml=yaml_text)
            schedule_flow(flow_dict)

            return jsonify({"ok": True, "flow_id": flow_id})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/flows/<flow_id>", methods=["DELETE"])
    @login_required
    def api_flows_delete(flow_id):
        try:
            from hecos.modules.flows.storage import delete_flow
            from hecos.modules.flows.engine import unschedule_flow
            unschedule_flow(flow_id)
            ok = delete_flow(flow_id)
            if not ok:
                return jsonify({"ok": False, "error": f"Flow '{flow_id}' not found."}), 404
            return jsonify({"ok": True})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/flows/<flow_id>/run", methods=["POST"])
    @login_required
    def api_flows_run(flow_id):
        try:
            from hecos.modules.flows.storage import get_flow
            from hecos.modules.flows.engine import run_flow_async, get_active_run
            # Prevent duplicate runs
            existing = get_active_run(flow_id)
            if existing:
                return jsonify({"ok": False, "error": "already_running", "run_id": existing}), 409
            flow_data = get_flow(flow_id)
            if flow_data is None:
                return jsonify({"ok": False, "error": f"Flow '{flow_id}' not found."}), 404
            run_id = run_flow_async(flow_data)
            return jsonify({"ok": True, "run_id": run_id})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/flows/<flow_id>/stop", methods=["POST"])
    @login_required
    def api_flows_stop(flow_id):
        """Abort the currently running execution of a flow."""
        try:
            from hecos.modules.flows.engine import get_active_run, abort_run
            run_id = get_active_run(flow_id)
            if not run_id:
                return jsonify({"ok": False, "error": "not_running"}), 404
            abort_run(run_id)
            return jsonify({"ok": True, "run_id": run_id})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/flows/<flow_id>/status", methods=["GET"])
    @login_required
    def api_flows_status(flow_id):
        """Return whether a flow is currently running and its active run_id."""
        try:
            from hecos.modules.flows.engine import get_active_run
            run_id = get_active_run(flow_id)
            return jsonify({"ok": True, "running": run_id is not None, "run_id": run_id})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/flows/<flow_id>/enable", methods=["POST"])
    @login_required
    def api_flows_enable(flow_id):
        try:
            from hecos.modules.flows.storage import update_flow_field, get_flow
            from hecos.modules.flows.engine import schedule_flow
            if not update_flow_field(flow_id, "enabled", True):
                return jsonify({"ok": False, "error": "Not found."}), 404
            flow_data = get_flow(flow_id)
            if flow_data:
                schedule_flow(flow_data)
            return jsonify({"ok": True})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/flows/<flow_id>/disable", methods=["POST"])
    @login_required
    def api_flows_disable(flow_id):
        try:
            from hecos.modules.flows.storage import update_flow_field
            from hecos.modules.flows.engine import unschedule_flow
            if not update_flow_field(flow_id, "enabled", False):
                return jsonify({"ok": False, "error": "Not found."}), 404
            unschedule_flow(flow_id)
            return jsonify({"ok": True})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/flows/compile", methods=["POST"])
    @login_required
    def api_flows_compile():
        try:
            payload     = request.get_json(force=True)
            description = payload.get("description", "").strip()
            flow_name   = payload.get("flow_name", "").strip() or None

            if not description:
                return jsonify({"ok": False, "error": "No description provided."}), 400

            from hecos.modules.flows.compiler import compile_from_nlp
            yaml_text, summary, flow_dict = compile_from_nlp(
                description=description,
                flow_name=flow_name,
            )
            return jsonify({
                "ok":      True,
                "yaml":    yaml_text,
                "summary": summary,
                "flow":    flow_dict,
            })
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/flows/validate", methods=["POST"])
    @login_required
    def api_flows_validate():
        try:
            payload   = request.get_json(force=True)
            yaml_text = payload.get("yaml", "")
            from hecos.modules.flows.validator import validate_yaml_string
            is_valid, errors, _ = validate_yaml_string(yaml_text)
            return jsonify({"ok": True, "valid": is_valid, "errors": errors})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/flows/actions/catalog", methods=["GET"])
    @login_required
    def api_flows_catalog():
        try:
            from hecos.modules.flows.registry import get_catalog, _auto_register_hecos_modules
            _auto_register_hecos_modules()
            return jsonify({"ok": True, "catalog": get_catalog()})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    # ── SSE: Real-time execution log ───────────────────────────────────────────

    @app.route("/api/flows/<flow_id>/log/stream", methods=["GET"])
    @login_required
    def api_flows_log_stream(flow_id):
        """SSE endpoint — subscribe to live events for the most recently started run."""
        from hecos.modules.flows.engine import get_event_bus

        # The run_id can be passed as a query param; if absent, we stream a "waiting" state
        run_id = request.args.get("run_id", "latest")
        bus    = get_event_bus()
        queue  = bus.subscribe(run_id)

        def _generate():
            try:
                # Send initial ping
                yield f"data: {json.dumps({'type': 'connected', 'run_id': run_id})}\n\n"
                timeout = time.time() + 300   # max 5 min stream
                while time.time() < timeout:
                    while queue:
                        event = queue.pop(0)
                        yield f"data: {json.dumps(event)}\n\n"
                        if event.get("type") == "stream_end":
                            return
                    time.sleep(0.15)
                yield f"data: {json.dumps({'type': 'timeout'})}\n\n"
            finally:
                bus.unsubscribe(run_id)

        return Response(
            stream_with_context(_generate()),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    _log.info("[Flows] Routes registered.")
