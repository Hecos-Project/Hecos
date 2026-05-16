"""
routes_system.py
────────────────────────────────────────────────────────────────────────────
Hecos WebUI — System Routes Orchestrator
This module owns:
  • The background CPU sampler (shared utility)
  • The VRAM helper
  • Core setup routes: /hecos/logs, /hecos/heartbeat, /assets/<path>
  • Sub-module delegation to all routes_system_*.py files

Sub-modules (each has its own init_*_routes function):
  routes_system_status.py     → GET  /hecos/status
  routes_system_control.py    → GET/POST /api/system/* + GET /api/events
  routes_system_memory.py     → POST /api/memory/clear, GET /api/memory/status
  routes_system_persona.py    → GET/POST /api/persona/avatar*
  routes_system_sysnet.py     → POST /api/system/reboot, GET /api/sysnet/test-proxy
  routes_system_diagnostic.py → POST /api/system/diagnostic/*, POST /api/browser/*
────────────────────────────────────────────────────────────────────────────
"""
import os
import json
import time
import threading
import sys
import subprocess
from flask import request, jsonify, render_template

# ── CPU background sampler ──────────────────────────────────────────────────
# psutil.cpu_percent() without interval= always returns 0.0 or 100% on first
# call because it has no baseline. We cache a reading every 2 seconds instead.
import psutil

_cpu_cache = {"value": 0.0, "enabled": True}
_last_cpu_times = None


def _cpu_sampler():
    global _last_cpu_times
    _last_cpu_times = psutil.cpu_times()
    while True:
        try:
            if _cpu_cache.get("enabled", True):
                current_times = psutil.cpu_times()
                t1_all  = sum(_last_cpu_times)
                t1_busy = t1_all - getattr(_last_cpu_times, "idle", 0.0)
                t2_all  = sum(current_times)
                t2_busy = t2_all - getattr(current_times, "idle", 0.0)
                if t2_all > t1_all:
                    busy_delta = max(0.0, t2_busy - t1_busy)
                    all_delta  = max(0.0, t2_all  - t1_all)
                    percent = (busy_delta / all_delta) * 100.0 if all_delta > 0 else 0.0
                    _cpu_cache["value"] = round(min(100.0, percent), 1)
                _last_cpu_times = current_times
                time.sleep(2)
            else:
                _last_cpu_times = psutil.cpu_times()
                time.sleep(5)
        except Exception:
            time.sleep(5)


_cpu_thread = threading.Thread(target=_cpu_sampler, daemon=True)
_cpu_thread.start()
# ──────────────────────────────────────────────────────────────────────────


def get_vram_usage():
    """Returns VRAM usage percentage via nvidia-smi, or 0 if unavailable."""
    try:
        cmd    = ["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,noheader,nounits"]
        kwargs = {}
        if sys.platform == "win32":
            kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            kwargs["startupinfo"] = startupinfo
        res = subprocess.check_output(cmd, encoding="utf-8", timeout=2, **kwargs).strip()
        if res:
            used, total = [int(x.strip()) for x in res.split(",")]
            if total > 0:
                return round((used / total) * 100, 1)
    except Exception:
        pass
    return 0


def init_system_routes(app, cfg_mgr, root_dir, logger, get_sm=None):
    # Sync telemetry flag from DASHBOARD plugin config
    global _cpu_cache
    dsb_cfg         = cfg_mgr.config.get("plugins", {}).get("DASHBOARD", {})
    global_enabled  = dsb_cfg.get("enabled", True)
    webui_telemetry = dsb_cfg.get("webui_telemetry_enabled", True)
    _cpu_cache["enabled"] = global_enabled and webui_telemetry

    def _sm():
        return get_sm() if callable(get_sm) else get_sm

    # ── Core routes registered directly (lightweight, no domain grouping) ──

    @app.route("/hecos/logs")
    def standalone_logs():
        try:
            from hecos.core.i18n.translator import get_translator
            translations = get_translator().get_translations()
            return render_template("standalone_logs.html",
                                   zconfig=cfg_mgr.config,
                                   translations=translations)
        except Exception as e:
            logger.error(f"Error serving standalone logs: {e}")
            return str(e), 500

    @app.route("/hecos/heartbeat", methods=["POST"])
    def heartbeat():
        try:
            import tempfile
            data      = request.get_json(force=True) or {}
            page_type = data.get("type", "unknown")
            hb_file   = os.path.join(tempfile.gettempdir(), "hecos_webui_heartbeat.json")
            hb_data   = {}
            if os.path.exists(hb_file):
                try:
                    with open(hb_file, "r") as f: hb_data = json.load(f)
                except: pass
            hb_data[page_type] = time.time()
            os.makedirs(os.path.dirname(hb_file), exist_ok=True)
            with open(hb_file, "w") as f: json.dump(hb_data, f)
            return jsonify({"ok": True})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/assets/<path:filename>")
    def serve_assets(filename):
        from flask import send_from_directory, make_response
        import mimetypes
        assets_dir = os.path.join(root_dir, "hecos", "assets")
        resp       = make_response(send_from_directory(assets_dir, filename))
        mtype, _   = mimetypes.guess_type(filename)
        if mtype:
            resp.headers["Content-Type"] = mtype
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        resp.headers["Pragma"]  = "no-cache"
        resp.headers["Expires"] = "0"
        return resp

    # ── Delegate to sub-route modules ──────────────────────────────────────

    from hecos.modules.web_ui.routes_system_status     import init_system_status_routes
    from hecos.modules.web_ui.routes_system_control    import init_system_control_routes
    from hecos.modules.web_ui.routes_system_memory     import init_system_memory_routes
    from hecos.modules.web_ui.routes_system_persona    import init_system_persona_routes
    from hecos.modules.web_ui.routes_system_sysnet     import init_system_sysnet_routes
    from hecos.modules.web_ui.routes_system_diagnostic import init_system_diagnostic_routes

    init_system_status_routes    (app, cfg_mgr, root_dir, logger, _sm, _cpu_cache, get_vram_usage)
    init_system_control_routes   (app, logger, _sm)
    init_system_memory_routes    (app, cfg_mgr, logger)
    init_system_persona_routes   (app, root_dir, logger)
    init_system_sysnet_routes    (app, logger)
    init_system_diagnostic_routes(app, cfg_mgr, logger)

    # ── Sub-application roots ──────────────────────────────────────────────
    from hecos.modules.web_ui.routes_explorer import init_explorer_routes
    from hecos.modules.web_ui.routes_bridge   import init_bridge_routes
    init_explorer_routes(app, logger)
    init_bridge_routes  (app, logger)
