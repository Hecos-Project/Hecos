"""
Telemetry Widget — WEB_UI Sidebar Extension
Provides its own autonomous REST API for reading and saving widget config (track_cpu/ram/vram)
to the package's own telemetry_widget.toml — zero dependency on core plugins.yaml.

Also provides process management endpoints for SwarmUI and system RAM cleanup.
"""
import threading
from flask import jsonify, request

try:
    from hecos.core.logging import logger
except ImportError:
    class _L:
        def debug(self, *a): pass
        def info(self, *a): pass
        def error(self, *a): pass
    logger = _L()

try:
    from .config_manager import get_config, save_config
except ImportError:
    try:
        from config_manager import get_config, save_config
    except ImportError:
        def get_config(): return type('C', (), {'track_cpu': False, 'track_ram': False, 'track_vram': False})()
        def save_config(d): return False


def _get_swarm_launcher():
    """Return the SwarmUILauncher singleton, or None if image_gen is not installed."""
    try:
        from hecos.hpm.image_gen.plugin.local.launcher import SwarmUILauncher
        return SwarmUILauncher.get_instance()
    except ImportError:
        try:
            from hpm.image_gen.plugin.local.launcher import SwarmUILauncher
            return SwarmUILauncher.get_instance()
        except ImportError:
            return None


def _get_local_cfg():
    """Return image_gen local config dict (url, install_path, auto_start, etc.)."""
    try:
        try:
            from hecos.hpm.image_gen.igen_config.config_manager import get_image_gen_config
        except ImportError:
            from hpm.image_gen.igen_config.config_manager import get_image_gen_config
        cfg = get_image_gen_config()
        return cfg.get('local', {})
    except Exception:
        return {}


def init_routes(app, root_dir: str = None):
    logger.debug("TelemetryWidget", "Telemetry sidebar dashboard widget loaded.")

    # ── Hardware monitoring config ─────────────────────────────────────────────

    @app.route("/api/telemetry_widget/config", methods=["GET"])
    def telemetry_widget_get_config():
        """Returns the current hardware monitoring settings from the package's own TOML."""
        try:
            cfg = get_config()
            return jsonify({
                "ok": True,
                "track_cpu":  cfg.track_cpu,
                "track_ram":  cfg.track_ram,
                "track_vram": cfg.track_vram,
            })
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/telemetry_widget/config", methods=["POST"])
    def telemetry_widget_save_config():
        """Saves hardware monitoring toggles to the package's own TOML. No core YAML involved."""
        try:
            data = request.get_json(force=True) or {}
            ok = save_config(data)
            return jsonify({"ok": ok})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    # ── SwarmUI process control ────────────────────────────────────────────────

    @app.route("/api/process/swarmui/status", methods=["GET"])
    def process_swarmui_status():
        """Returns SwarmUI running status, URL, version, RAM usage."""
        try:
            launcher = _get_swarm_launcher()
            if launcher is None:
                return jsonify({"ok": False, "error": "image_gen module not installed", "running": False})

            local_cfg = _get_local_cfg()
            st = launcher.check_status(local_cfg)
            ram_info = launcher.get_ram_usage_mb()

            return jsonify({
                "ok": True,
                "running":      st.get("running", False),
                "starting":     st.get("starting", False),
                "installed":    st.get("installed", False),
                "status_code":  st.get("status_code", "UNKNOWN"),
                "status_text":  st.get("status_text", ""),
                "url":          st.get("url", ""),
                "version":      st.get("version", ""),
                "latency_ms":   st.get("latency_ms", 0),
                "install_path": st.get("install_path", ""),
                "ram_mb":       ram_info.get("ram_mb", 0),
                "pid_count":    ram_info.get("pid_count", 0),
            })
        except Exception as e:
            return jsonify({"ok": False, "error": str(e), "running": False}), 500

    @app.route("/api/process/swarmui/stop", methods=["POST"])
    def process_swarmui_stop():
        """Kill SwarmUI process tree to free RAM/VRAM."""
        try:
            launcher = _get_swarm_launcher()
            if launcher is None:
                return jsonify({"ok": False, "error": "image_gen module not installed"})
            result = launcher.stop()
            return jsonify(result)
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/process/swarmui/start", methods=["POST"])
    def process_swarmui_start():
        """Start SwarmUI in background (async, returns immediately)."""
        try:
            launcher = _get_swarm_launcher()
            if launcher is None:
                return jsonify({"ok": False, "error": "image_gen module not installed"})

            local_cfg = _get_local_cfg()

            def _start_bg():
                try:
                    launcher.ensure_running(local_cfg, force_start=True)
                except Exception:
                    pass

            t = threading.Thread(target=_start_bg, daemon=True, name="swarmui-start-bg")
            t.start()
            return jsonify({"ok": True, "message": "SwarmUI start initiated in background."})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    # ── System RAM cleanup ─────────────────────────────────────────────────────

    @app.route("/api/system/free_ram", methods=["POST"])
    def system_free_ram():
        """
        Multi-step RAM cleanup:
        1. Stop SwarmUI (if running)
        2. Optionally unload Ollama model (keep_alive=0)
        Steps requested via JSON body: { stop_swarmui, unload_ollama }
        """
        try:
            data = request.get_json(force=True) or {}
            stop_swarmui  = data.get("stop_swarmui", True)
            unload_ollama = data.get("unload_ollama", False)

            report = []
            freed_mb = 0

            # Step 1: stop SwarmUI
            if stop_swarmui:
                launcher = _get_swarm_launcher()
                if launcher:
                    ram_before = launcher.get_ram_usage_mb().get("ram_mb", 0)
                    result = launcher.stop()
                    freed_mb += ram_before
                    if result.get("ok"):
                        report.append(f"SwarmUI stopped. Freed ~{ram_before} MB RAM.")
                    else:
                        report.append(f"SwarmUI stop: {result.get('message', 'done')}")
                else:
                    report.append("SwarmUI: image_gen module not installed, skipped.")

            # Step 2: unload Ollama model
            if unload_ollama:
                try:
                    import requests as _req
                    # keep_alive=0 tells Ollama to immediately evict the model from VRAM
                    r = _req.post(
                        "http://localhost:11434/api/generate",
                        json={"model": "", "keep_alive": 0},
                        timeout=5
                    )
                    if r.status_code < 400:
                        report.append("Ollama: model unloaded from VRAM (keep_alive=0).")
                        freed_mb += 8000  # rough VRAM estimate, actual varies
                    else:
                        report.append(f"Ollama unload: HTTP {r.status_code}.")
                except Exception as exc:
                    report.append(f"Ollama unload error: {exc}")

            return jsonify({
                "ok": True,
                "freed_mb_estimate": freed_mb,
                "report": report,
            })
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500
