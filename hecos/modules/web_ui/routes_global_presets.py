"""
hecos/modules/web_ui/routes_global_presets.py
REST API for Soul Forge (Global Presets), Session Drafts, Quick Test Lab, and Inference Presets.
"""

import re
import time
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
            data = request.json or {}
            soul_id = data.get("soul_id")
            session_id = data.get("session_id")
            
            if soul_id is None:
                return jsonify({"ok": False, "error": "Missing soul_id"}), 400
                
            soul = None
            if soul_id != "":
                soul = get_soul(soul_id)
                if not soul:
                    return jsonify({"ok": False, "error": "Soul not found"}), 404
            elif "soul" in data and data["soul"]:
                soul = SoulProfile.model_validate(data["soul"])
                
            logger.info(f"[GlobalPresets] /activate: soul_id='{soul_id}', session_id='{session_id}', soul_name='{soul.meta.name if soul else 'None'}'")
            
            if not session_id or session_id == "global":
                # Set system-wide default
                if cfg_mgr:
                    patch = {}
                    patch.setdefault("ai", {})["active_global_preset"] = soul_id
                    if soul:
                        if soul.persona.soul_file:
                            patch["ai"]["active_personality"] = soul.persona.soul_file
                        if soul.persona.use_global_direct_instructions is not None:
                            patch["ai"]["use_global_direct_instructions"] = soul.persona.use_global_direct_instructions
                        if soul.persona.use_global_safety_instructions is not None:
                            patch["ai"]["use_global_safety_instructions"] = soul.persona.use_global_safety_instructions
                        if soul.persona.custom_instructions is not None:
                            patch["ai"]["custom_instructions"] = soul.persona.custom_instructions
                        if soul.persona.user_notes is not None:
                            patch["ai"]["user_notes"] = soul.persona.user_notes
                        if soul.persona.send_notes_to_ai is not None:
                            patch["ai"]["send_notes_to_ai"] = soul.persona.send_notes_to_ai

                        if soul.payload:
                            p_ctrl = patch.setdefault("payload_control", {})
                            if soul.payload.send_tools is not None:
                                p_ctrl["send_tools"] = soul.payload.send_tools
                            if soul.payload.send_personality is not None:
                                p_ctrl["send_personality"] = soul.payload.send_personality
                            if soul.payload.send_memory is not None:
                                p_ctrl["send_memory"] = soul.payload.send_memory
                            if soul.payload.include_thinking_in_history is not None:
                                p_ctrl["include_thinking_in_history"] = soul.payload.include_thinking_in_history

                        if soul.voice.tts_engine:
                            patch.setdefault("ai", {})["tts_engine"] = soul.voice.tts_engine
                            patch.setdefault("audio", {})["active_engine"] = soul.voice.tts_engine
                        if soul.voice.tts_voice:
                            patch.setdefault("ai", {})["tts_voice"] = soul.voice.tts_voice

                        btype = soul.model.backend_type or cfg_mgr.config.get("backend", {}).get("type", "ollama")
                        if soul.model.backend_type:
                            patch.setdefault("backend", {})["type"] = btype
                            if soul.model.model_name:
                                patch["backend"].setdefault(btype, {})["model"] = soul.model.model_name

                        if soul.inference:
                            b_patch = patch.setdefault("backend", {}).setdefault(btype, {})
                            inf_dump = soul.inference.model_dump(exclude_none=True)
                            for k in ("temperature", "top_p", "repeat_penalty", "num_predict", "num_ctx", "n_gpu_layers"):
                                if k in inf_dump:
                                    b_patch[k] = inf_dump[k]
                                    if k == "n_gpu_layers":
                                        b_patch["num_gpu"] = inf_dump[k]

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
                                
                                if soul.voice.tts_engine == 'kokoro':
                                    acfg['active_engine'] = 'kokoro'
                                    k_cfg = acfg.setdefault('kokoro', {})
                                    if soul.voice.tts_voice:
                                        k_cfg['voice'] = soul.voice.tts_voice
                                    if soul.voice.kokoro_voice:
                                        k_cfg['voice'] = soul.voice.kokoro_voice
                                    if soul.voice.kokoro_blend_voice is not None:
                                        k_cfg['blend_voice'] = soul.voice.kokoro_blend_voice
                                    if soul.voice.kokoro_speed is not None:
                                        k_cfg['speed'] = soul.voice.kokoro_speed
                                    if soul.voice.kokoro_alpha is not None:
                                        k_cfg['alpha'] = soul.voice.kokoro_alpha
                                    if soul.voice.kokoro_beta is not None:
                                        k_cfg['beta'] = soul.voice.kokoro_beta
                                    if soul.voice.kokoro_silence is not None:
                                        k_cfg['sentence_silence'] = soul.voice.kokoro_silence
                                    if soul.voice.kokoro_volume is not None:
                                        k_cfg['volume'] = soul.voice.kokoro_volume
                                    if soul.voice.kokoro_normalize is not None:
                                        k_cfg['normalize'] = soul.voice.kokoro_normalize
                                    if soul.voice.kokoro_preset:
                                        k_cfg['current_preset'] = soul.voice.kokoro_preset
                                    if soul.voice.kokoro_inference_preset:
                                        k_cfg['current_inference_preset'] = soul.voice.kokoro_inference_preset

                                if soul.voice.tts_engine in ('fish_speech', 'fish'):
                                    acfg['active_engine'] = 'fish_speech'
                                    f_cfg = acfg.setdefault('fish_speech', {})
                                    ref_aud = soul.voice.fish_reference_audio or soul.voice.tts_voice
                                    if ref_aud:
                                        f_cfg['reference_audio'] = ref_aud
                                    if soul.voice.fish_reference_text is not None:
                                        f_cfg['reference_text'] = soul.voice.fish_reference_text
                                    if soul.voice.fish_temperature is not None:
                                        f_cfg['temperature'] = soul.voice.fish_temperature
                                    if soul.voice.fish_top_p is not None:
                                        f_cfg['top_p'] = soul.voice.fish_top_p
                                    if soul.voice.fish_repetition_penalty is not None:
                                        f_cfg['repetition_penalty'] = soul.voice.fish_repetition_penalty
                                    if soul.voice.fish_chunk_length is not None:
                                        f_cfg['chunk_length'] = soul.voice.fish_chunk_length
                                    if soul.voice.fish_max_new_tokens is not None:
                                        f_cfg['max_new_tokens'] = soul.voice.fish_max_new_tokens
                                    if soul.voice.fish_preset:
                                        f_cfg['current_preset'] = soul.voice.fish_preset
                                    else:
                                        f_cfg['current_preset'] = ""
                            _save_audio_config(acfg)
                            if soul.voice and soul.voice.tts_engine in ('fish_speech', 'fish'):
                                from hecos.core.audio.tts.fish_speech_daemon import FishSpeechDaemon
                                daemon = FishSpeechDaemon.get_instance()
                                if daemon.is_local_target() and not daemon.is_healthy():
                                    daemon.preload(delay=0.2)
                        except Exception as e:
                            logger.error(f"[GlobalPresets] Error updating audio.yaml: {e}")
            else:
                from hecos.memory.session_config_db import set_session_config, get_session_config
                overrides = get_session_config(session_id) or {}
                
                if soul:
                    # Clear previous overrides so old values don't bleed through
                    for k in ['ai', 'backend', 'inference', 'voice', 'persona', 'model', 'payload', 'payload_control', 'draft']:
                        if k in overrides:
                            del overrides[k]
                            
                    overrides['active_global_preset'] = soul_id
                    overrides['ai'] = {}
                    
                    if soul.persona.soul_file: overrides['ai']['active_personality'] = soul.persona.soul_file
                    if soul.voice.tts_engine: overrides['ai']['tts_engine'] = soul.voice.tts_engine
                    if soul.voice.tts_voice: overrides['ai']['tts_voice'] = soul.voice.tts_voice
                    
                    overrides['persona'] = soul.persona.model_dump(exclude_none=True)
                    overrides['model'] = soul.model.model_dump(exclude_none=True)
                    
                    if soul.model.backend_type:
                        if 'backend' not in overrides: overrides['backend'] = {}
                        btype = soul.model.backend_type
                        overrides['backend']['type'] = btype
                        if soul.model.model_name:
                            if btype not in overrides['backend']: overrides['backend'][btype] = {}
                            overrides['backend'][btype]['model'] = soul.model.model_name
                            
                    if soul.inference:
                        overrides['inference'] = soul.inference.model_dump(exclude_none=True)
                            
                    if soul.voice:
                        overrides['voice'] = soul.voice.model_dump(exclude_none=True)

                    if soul.payload:
                        p_dump = soul.payload.model_dump(exclude_none=True)
                        overrides['payload'] = p_dump
                        overrides['payload_control'] = dict(p_dump)
                else:
                    # The user selected "No active global preset" or clicked Reset, so we clear all overrides
                    overrides = {}
                
                set_session_config(session_id, overrides)
            
            if soul:
                logger.info(f"[GlobalPresets] About to emit persona_switched for '{soul.persona.soul_file}'")
                from hecos.core.events import emit
                emit("persona_switched", {"new_persona": soul.persona.soul_file})
                logger.info("[GlobalPresets] persona_switched emitted OK")
            else:
                logger.info("[GlobalPresets] No soul, skipping emit")

            return jsonify({"ok": True, "soul": soul.model_dump() if soul else None})
        except Exception as e:
            logger.error(f"[GlobalPresets] Error activating soul: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    # ── Quick Test Lab (Ephemeral LLM Test without polluting chat history) ──

    @app.route("/api/souls/test", methods=["POST"])
    def api_test_soul_config():
        try:
            data = request.json or {}
            prompt = (data.get("prompt") or "Briefly introduce yourself in two sentences.").strip()
            session_id = data.get("session_id")
            draft = data.get("draft")

            active_cfg_mgr = cfg_mgr
            if active_cfg_mgr is None:
                import sys as _sys
                active_cfg_mgr = getattr(_sys, "hecos_config_manager", None)

            base_config = active_cfg_mgr.config if active_cfg_mgr else None
            if not base_config:
                from hecos.core.llm.brain import load_config
                base_config = load_config() or {}

            from hecos.config.session_config_manager import merge_session_config
            merged_cfg = merge_session_config(base_config, session_id=session_id, extra_draft=draft)

            from hecos.core.llm.brain import generate_response
            from hecos.core.llm.client import LAST_PAYLOAD_INFO

            t0 = time.monotonic()
            raw_response = generate_response(
                prompt,
                external_config=merged_cfg,
                save_history=False,
                session_id=session_id
            )
            elapsed = round(time.monotonic() - t0, 2)

            text_out = raw_response if isinstance(raw_response, str) else str(raw_response or "")
            thinking_out = ""

            # Extract <think>...</think> if present
            think_match = re.search(r"<think>([\s\S]*?)</think>", text_out, flags=re.IGNORECASE)
            if think_match:
                thinking_out = think_match.group(1).strip()
                text_out = re.sub(r"<think>[\s\S]*?</think>", "", text_out, flags=re.IGNORECASE).strip()
            elif "</think>" in text_out:
                parts = text_out.split("</think>", 1)
                thinking_out = parts[0].strip()
                text_out = parts[1].strip()

            # Unwrap JSON fallback if model returned {"response": ...}
            if text_out.startswith("{") and text_out.endswith("}"):
                try:
                    import json as _json
                    parsed = _json.loads(text_out)
                    if isinstance(parsed, dict) and "response" in parsed:
                        r_val = parsed["response"]
                        if isinstance(r_val, dict) and "text" in r_val:
                            text_out = r_val["text"]
                        elif isinstance(r_val, str):
                            text_out = r_val
                except Exception:
                    pass

            btype = merged_cfg.get("backend", {}).get("type", "ollama")
            if btype == "hybrid":
                btype = merged_cfg.get("backend", {}).get("active_model_source", "cloud")
            b_dict = merged_cfg.get("backend", {}).get(btype, {}) or {}
            p_ctrl = merged_cfg.get("payload_control", {}) or {}

            comp_tokens = LAST_PAYLOAD_INFO.get("completion_tokens") or max(1, len(text_out) // 4)
            prompt_tokens = LAST_PAYLOAD_INFO.get("prompt_tokens") or LAST_PAYLOAD_INFO.get("est_tokens", 0)
            tok_per_sec = round(comp_tokens / elapsed, 1) if elapsed > 0 else 0
            last_p_ctrl = LAST_PAYLOAD_INFO.get("payload_control") or {}

            metrics = {
                "elapsed_sec": elapsed,
                "model": LAST_PAYLOAD_INFO.get("model") or b_dict.get("model", "unknown"),
                "backend": btype,
                "temperature": b_dict.get("temperature", 0.7),
                "top_p": b_dict.get("top_p", 0.9),
                "prompt_tokens": prompt_tokens,
                "completion_tokens": comp_tokens,
                "tok_per_sec": tok_per_sec,
                "system_chars": LAST_PAYLOAD_INFO.get("system_chars", 0),
                "tools_count": last_p_ctrl.get("tools_count", 0),
                "send_tools": p_ctrl.get("send_tools", True),
                "send_personality": p_ctrl.get("send_personality", True),
                "send_memory": p_ctrl.get("send_memory", True),
                "include_thinking": p_ctrl.get("include_thinking_in_history", False),
            }

            return jsonify({
                "ok": True,
                "response": text_out,
                "thinking": thinking_out,
                "metrics": metrics
            })
        except Exception as e:
            logger.error(f"[GlobalPresets] Error in /api/souls/test: {e}", exc_info=True)
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
