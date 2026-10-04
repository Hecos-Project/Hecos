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

def init_global_presets_routes(app, root_dir, logger, cfg_mgr=None):

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
            
            if soul_id is None:
                return jsonify({"ok": False, "error": "Missing soul_id"}), 400
                
            soul = None
            if soul_id != "":
                soul = get_soul(soul_id)
                if not soul:
                    return jsonify({"ok": False, "error": "Soul not found"}), 404
                
            if not session_id or session_id == "global":
                # Set system-wide default
                if cfg_mgr:
                    patch = {}
                    patch.setdefault("ai", {})["active_global_preset"] = soul_id
                    if soul:
                        if soul.persona.soul_file:
                            patch["ai"]["active_personality"] = soul.persona.soul_file
                        if soul.voice.tts_engine:
                            patch.setdefault("ai", {})["tts_engine"] = soul.voice.tts_engine
                            patch.setdefault("audio", {})["active_engine"] = soul.voice.tts_engine
                        if soul.voice.tts_voice:
                            patch.setdefault("ai", {})["tts_voice"] = soul.voice.tts_voice
                        if soul.model.backend_type:
                            btype = soul.model.backend_type
                            patch.setdefault("backend", {})["type"] = btype
                            if soul.model.model_name:
                                patch["backend"].setdefault(btype, {})["model"] = soul.model.model_name
                    cfg_mgr.update_from_webui(patch)
                    
                    # Update audio config if global
                    if soul:
                        try:
                            from hecos.core.audio.device_manager import get_audio_config, _save_audio_config
                            acfg = get_audio_config()
                            if soul.voice:
                                for k, v in soul.voice.model_dump(exclude_unset=True).items():
                                    if k in acfg.get('xtts', {}):
                                        acfg['xtts'][k] = v if v is not None else ""
                                    elif k in acfg.get('kokoro', {}):
                                        acfg['kokoro'][k] = v if v is not None else ""
                                        
                                if 'tts_voice' in soul.voice.model_dump(exclude_unset=True):
                                    v = soul.voice.tts_voice
                                    if v is not None:
                                        acfg.setdefault('xtts', {})['speaker'] = v
                                        acfg.setdefault('kokoro', {})['voice'] = v
                                        
                                # Map correctly for audio.yaml schema
                                if 'xtts_preset' in soul.voice.model_dump(exclude_unset=True):
                                    acfg['xtts']['current_preset'] = soul.voice.xtts_preset if soul.voice.xtts_preset is not None else "default"
                                if soul.voice.xtts_inference_preset is not None:
                                    pass # this doesn't directly exist in audio.yaml root/xtts, wait...
                            _save_audio_config(acfg)
                        except Exception as e:
                            logger.error(f"[GlobalPresets] Error updating audio.yaml: {e}")
            else:
                from hecos.memory.session_config_db import set_session_config, get_session_config
                overrides = get_session_config(session_id) or {}
                overrides['active_global_preset'] = soul_id
                
                # Optionally populate ai/backend overrides if we want UI dropdowns to reflect them
                if soul:
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
                            
                    if soul.inference:
                        if 'inference' not in overrides: overrides['inference'] = {}
                        for k, v in soul.inference.model_dump(exclude_unset=True).items():
                            overrides['inference'][k] = v
                            
                    if soul.voice:
                        if 'voice' not in overrides: overrides['voice'] = {}
                        for k, v in soul.voice.model_dump(exclude_unset=True).items():
                            overrides['voice'][k] = v
                
                set_session_config(session_id, overrides)
            
            return jsonify({"ok": True, "soul": soul.model_dump() if soul else None})
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
