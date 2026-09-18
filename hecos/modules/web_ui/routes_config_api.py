"""
hecos/modules/web_ui/routes_config_api.py
REST API endpoints for configuration management (save/load/options).
"""
import os
import glob
import time
from flask import request, jsonify
from hecos.core.logging import logger

# ── Server-side options cache ─────────────────────────────────────────────────
# Avoids expensive YAML reload + filesystem glob + personality sync on every
# tab click or /hecos/options request. Invalidated on config save or after TTL.
_OPTIONS_CACHE: dict = {}
_OPTIONS_CACHE_TS: float = 0.0
_OPTIONS_CACHE_TTL: float = 60.0  # seconds


def _invalidate_options_cache():
    """Call this after a config save to force a fresh build on next request."""
    global _OPTIONS_CACHE_TS
    _OPTIONS_CACHE_TS = 0.0


def _build_options_dict(cfg_mgr, fast=False):
    """Build the zoptions dict containing model lists, Piper voices, personalities.
    Results are cached in memory for _OPTIONS_CACHE_TTL seconds to avoid
    repeated disk I/O and filesystem scans on every tab click.
    """
    global _OPTIONS_CACHE, _OPTIONS_CACHE_TS

    now = time.monotonic()
    if _OPTIONS_CACHE and (now - _OPTIONS_CACHE_TS) < _OPTIONS_CACHE_TTL:
        return _OPTIONS_CACHE

    cfg = cfg_mgr.config

    hecos_root  = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    piper_path_dir = os.path.join(hecos_root, 'bin', 'piper')
    try:
        onnx_files = [os.path.basename(f) for f in glob.glob(os.path.join(piper_path_dir, "*.onnx"))]
        if not onnx_files:
            onnx_files = ["it_IT-aurora-medium.onnx"]
    except Exception:
        onnx_files = ["it_IT-aurora-medium.onnx"]

    categorized   = {}
    ollama_models = []
    try:
        from hecos.app.model_manager import ModelManager
        mm = ModelManager(cfg_mgr)
        categorized   = mm.get_available_models(fast_mode=True)
        ollama_models = categorized.get("Ollama (Local)", [])
    except Exception as _mm_e:
        import traceback as _tb
        logger.error(f"[WebUI] ModelManager failed in _build_options_dict: {_mm_e}\n{_tb.format_exc()}")

    try:
        cfg_mgr.sync_available_personalities()
        personalita = list(cfg_mgr.config.get("ai", {}).get("available_personalities", {}).values())
    except Exception as _p_e:
        logger.error(f"[WebUI] sync_available_personalities failed: {_p_e}")
        personalita = []

    cloud_models_flat = []
    cloud_by_provider = {}
    for cat, models in categorized.items():
        if "Cloud" in cat:
            cloud_models_flat.extend(models)
            provider = cat.replace("Cloud (", "").replace(")", "").lower()
            cloud_by_provider[provider] = models

    result = {
        "piper_voices":  onnx_files,
        "piper_dir":     piper_path_dir,
        "ollama_models": ollama_models,
        "llamacpp_models": categorized.get("LlamaCPP (Local)", []),
        "personalities": personalita,
        "cloud_models":  cloud_by_provider,
        "all_cloud":     cloud_models_flat,
    }

    _OPTIONS_CACHE    = result
    _OPTIONS_CACHE_TS = now
    return result


def register_config_api_routes(app, cfg_mgr, get_sm=None):
    """Register REST endpoints for configuration."""

    @app.route("/hecos/config", methods=["GET"])
    def get_config():
        """Returns the in-memory YAML configuration."""
        try:
            return jsonify(cfg_mgr.config)
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    @app.route("/hecos/config", methods=["POST"])
    def post_config():
        """Saves configuration updates to disk and applies changes."""
        try:
            data = request.json
            if data is None:
                return jsonify({"ok": False, "error": "No JSON provided"}), 400

            success = cfg_mgr.update_from_webui(data)
            if success:
                def _bg_sync(cfg_snapshot):
                    try:
                        from hecos.core.system import module_loader
                        from hecos.core.processing import filtri
                        module_loader.update_capability_registry(cfg_snapshot, debug_log=False)
                        filtri.reset_cache()
                        logger.debug("[WebUI] Background processor sync completed.")
                    except Exception as e:
                        logger.debug(f"[WebUI] Processor background sync error: {e}")

                import threading
                import copy
                threading.Thread(target=_bg_sync, args=(copy.deepcopy(cfg_mgr.config),), daemon=True).start()

                _invalidate_options_cache()

                return jsonify({"ok": True})
            return jsonify({"ok": False, "error": "Save failed"}), 500
        except Exception as exc:
            logger.error(f"[WebUI] POST /config error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route("/hecos/options", methods=["GET"])
    def get_options():
        """Returns cached options for dropdowns."""
        return jsonify(_build_options_dict(cfg_mgr, fast=True))

    @app.route("/hecos/config/clear-cli-history", methods=["POST"])
    def clear_cli_history():
        """Clears the terminal CLI input history."""
        try:
            from hecos.ui import terminal_input
            terminal_input._cli_history = []
            terminal_input._cli_history_idx = -1
            terminal_input._cli_history_draft = ""
            hist_path = os.path.join(cfg_mgr.data_dir, "cli_history.json")
            if os.path.exists(hist_path):
                os.remove(hist_path)
            return jsonify({"ok": True})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500
