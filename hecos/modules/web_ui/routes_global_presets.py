"""
hecos/modules/web_ui/routes_global_presets.py
REST API for Soul Forge (Global Presets) and Inference Presets.
"""

from flask import request, jsonify
from hecos.core.logging import logger
from hecos.core.global_presets import (
    list_souls, get_soul, save_soul, delete_soul, SoulProfile,
    list_inference_presets, get_inference_preset, save_inference_preset, delete_inference_preset, InferencePreset
)

def init_global_presets_routes(app, root_dir, logger):

    # ── Souls (Global Presets) ──

    @app.route("/api/souls", methods=["GET"])
    def api_get_souls():
        try:
            souls = list_souls()
            return jsonify({"ok": True, "souls": [s.model_dump() for s in souls]})
        except Exception as e:
            logger.error(f"[GlobalPresets] Error listing souls: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/souls/<soul_id>", methods=["GET"])
    def api_get_soul(soul_id):
        try:
            soul = get_soul(soul_id)
            if soul:
                return jsonify({"ok": True, "soul": soul.model_dump()})
            return jsonify({"ok": False, "error": "Not found"}), 404
        except Exception as e:
            logger.error(f"[GlobalPresets] Error getting soul {soul_id}: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/souls", methods=["POST"])
    def api_save_soul():
        try:
            data = request.json
            soul = SoulProfile.model_validate(data)
            if save_soul(soul):
                return jsonify({"ok": True, "soul_id": soul.meta.id})
            return jsonify({"ok": False, "error": "Save failed"}), 500
        except Exception as e:
            logger.error(f"[GlobalPresets] Error saving soul: {e}")
            return jsonify({"ok": False, "error": str(e)}), 400

    @app.route("/api/souls/<soul_id>", methods=["DELETE"])
    def api_delete_soul(soul_id):
        try:
            if delete_soul(soul_id):
                return jsonify({"ok": True})
            return jsonify({"ok": False, "error": "Not found or delete failed"}), 404
        except Exception as e:
            logger.error(f"[GlobalPresets] Error deleting soul {soul_id}: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500
            
    @app.route("/api/souls/activate", methods=["POST"])
    def api_activate_soul():
        try:
            data = request.json
            soul_id = data.get("soul_id")
            session_id = data.get("session_id")
            
            if not soul_id or not session_id:
                return jsonify({"ok": False, "error": "Missing soul_id or session_id"}), 400
                
            soul = get_soul(soul_id)
            if not soul:
                return jsonify({"ok": False, "error": "Soul not found"}), 404
                
            from hecos.memory.session_config_db import set_session_config, get_session_config
            overrides = get_session_config(session_id) or {}
            overrides['active_global_preset'] = soul_id
            
            # Optionally populate ai/backend overrides if we want UI dropdowns to reflect them
            if 'ai' not in overrides: overrides['ai'] = {}
            if soul.persona.soul_file: overrides['ai']['active_personality'] = soul.persona.soul_file
            if soul.voice.tts_engine: overrides['ai']['tts_engine'] = soul.voice.tts_engine
            if soul.voice.tts_voice: overrides['ai']['tts_voice'] = soul.voice.tts_voice
            
            if soul.model.backend_type:
                if 'backend' not in overrides: overrides['backend'] = {}
                btype = soul.model.backend_type
                overrides['backend']['type'] = btype
                if soul.model.model_name:
                    if btype not in overrides['backend']: overrides['backend'][btype] = {}
                    overrides['backend'][btype]['model'] = soul.model.model_name
            
            set_session_config(session_id, overrides)
            
            return jsonify({"ok": True, "soul": soul.model_dump()})
        except Exception as e:
            logger.error(f"[GlobalPresets] Error activating soul: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    # ── Inference Presets ──

    @app.route("/api/souls/presets/inference", methods=["GET"])
    def api_get_inference_presets():
        try:
            presets = list_inference_presets()
            return jsonify({"ok": True, "presets": {k: v.model_dump() for k, v in presets.items()}})
        except Exception as e:
            logger.error(f"[GlobalPresets] Error listing inference presets: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/souls/presets/inference/<name>", methods=["POST"])
    def api_save_inference_preset(name):
        try:
            data = request.json
            preset = InferencePreset.model_validate(data)
            if save_inference_preset(name, preset):
                return jsonify({"ok": True})
            return jsonify({"ok": False, "error": "Save failed"}), 500
        except Exception as e:
            logger.error(f"[GlobalPresets] Error saving inference preset {name}: {e}")
            return jsonify({"ok": False, "error": str(e)}), 400

    @app.route("/api/souls/presets/inference/<name>", methods=["DELETE"])
    def api_delete_inference_preset(name):
        try:
            if delete_inference_preset(name):
                return jsonify({"ok": True})
            return jsonify({"ok": False, "error": "Not found or delete failed"}), 404
        except Exception as e:
            logger.error(f"[GlobalPresets] Error deleting inference preset {name}: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500
