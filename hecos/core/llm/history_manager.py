import json
import re
from hecos.core.logging import logger
from hecos.memory import brain_interface

class HistoryManager:
    """
    Handles saving the final AI response and the user message to the chat history database,
    stripping out reasoning tags and parsing JSON fallbacks.
    """
    
    @staticmethod
    def save_interaction(user_text, response, save_history, config, user_id, session_id, sender_tab_id, personality_name, backend_config):
        # Filter error messages (don't save them to history to avoid loops/bloat)
        is_error = False
        if isinstance(response, str) and (response.startswith("⚠️") or "Error" in response):
            is_error = True

        # Build generation parameters JSON unconditionally on non-error turns so multi-turn
        # Agentic Loop calls (which pass save_history=False) still populate LAST_PAYLOAD_INFO["model_info"].
        _model_info_str = None
        if not is_error:
            llm_config = (config or {}).get("llm", {}) if isinstance(config, dict) else {}
            _model_info_str = HistoryManager._build_model_info(backend_config, llm_config, config)

        if not is_error and save_history:
            # Snapshot the clean persona name so avatar stays correct even if user changes personality later
            clean_persona = personality_name.replace(".yaml", "") if personality_name else "Hecos_System_Soul"
            already_has_trailing_user = HistoryManager._has_trailing_matching_user_msg(user_text, user_id=user_id, session_id=session_id)
            if not already_has_trailing_user:
                brain_interface.save_message("user", user_text, config=config, user_id=user_id, session_id=session_id, sender_tab_id=sender_tab_id)
            
            # Structured response management (String or Message with tool_calls)
            if isinstance(response, str):
                logger.debug("HistoryManager", f"Response received from backend: {len(response)} characters")
                # Sanitize: if the model returned raw JSON (wrapper or inline tool calls),
                # save only the clean prose so history never stores raw tool JSON on crash/abort.
                _text_to_save = response
                try:
                    _stripped = response.strip()
                    if _stripped.startswith("{") and _stripped.endswith("}"):
                        _parsed = json.loads(_stripped)
                        if isinstance(_parsed, dict) and "response" in _parsed:
                            _resp = _parsed["response"]
                            if isinstance(_resp, dict) and "text" in _resp:
                                _text_to_save = _resp["text"]
                            elif isinstance(_resp, str):
                                _text_to_save = _resp
                except Exception:
                    pass

                try:
                    if "__" in _text_to_save and '"name"' in _text_to_save and '"arguments"' in _text_to_save:
                        from hecos.core.processing.parsers.json_fallback_parser import JsonFallbackParser
                        _inline_tags = []
                        _cleaned_text, _ = JsonFallbackParser.parse(_text_to_save, _inline_tags, None)
                        if _inline_tags:
                            logger.debug(
                                "HistoryManager",
                                f"Stripped {len(_inline_tags)} inline JSON tool call(s) before history save."
                            )
                            _text_to_save = _cleaned_text
                            if not _text_to_save.strip():
                                logger.debug("HistoryManager", "Skipping empty tool-only assistant message persistence.")
                                return
                except Exception as _jerr:
                    logger.debug("HistoryManager", f"Inline JSON history sanitize skipped: {_jerr}")
                
                # Keep thinking blocks intact so reasoning appears on page refresh.
                # The frontend JS (appendMessage) will extract and hide them properly.
                # (We no longer strip them here)
                    
                brain_interface.save_message("assistant", _text_to_save, config=config, user_id=user_id, session_id=session_id, persona_name=clean_persona, sender_tab_id=sender_tab_id, model_info=_model_info_str)
            else:
                # It's a Message object (used a tool)
                logger.debug("HistoryManager", "Response is a tool call object.")
                tool_names = [call.function.name for call in getattr(response, 'tool_calls', [])]
                logger.debug("HistoryManager", f"Tool calls generated: {', '.join(tool_names)} (NOT saving to DB to avoid UI clutter)")
        elif not save_history:
            logger.debug("HistoryManager", "save_history is False; skipping history persistence for this Agentic Loop turn.")
        else:
            logger.debug("HistoryManager", "AI response is an error; skipping history persistence.")
            
    @staticmethod
    def _has_trailing_matching_user_msg(user_text, user_id="admin", session_id=None) -> bool:
        """Returns True if the latest stored message in the session is already an unanswered user message with the same text."""
        try:
            clean_text = (user_text or "").strip()
            if not clean_text:
                return False
            from hecos.core.privacy import privacy_manager
            sid = session_id or privacy_manager.get_session_id()
            if not sid:
                return False

            from hecos.memory.session_state import _ram_sessions
            if sid in _ram_sessions:
                msgs = _ram_sessions[sid].get("messages", [])
                if msgs and msgs[-1].get("role") == "user" and (msgs[-1].get("message") or "").strip() == clean_text:
                    return True
                return False

            import os, sqlite3
            db_path = brain_interface._db_path(user_id or "admin")
            if not os.path.exists(db_path):
                return False
            with sqlite3.connect(db_path, timeout=10) as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT role, message FROM history WHERE session_id = ? ORDER BY id DESC LIMIT 1",
                    (sid,)
                )
                row = cur.fetchone()
                if row and row[0] == "user" and (row[1] or "").strip() == clean_text:
                    return True
        except Exception:
            pass
        return False

    @staticmethod
    def _build_model_info(backend_config, llm_config, full_config=None):
        _model_info_str = None
        if backend_config or llm_config:
            b_cfg = backend_config or {}
            l_cfg = llm_config or {}
            
            _m_name = b_cfg.get("model", "unknown")
            _m_backend = b_cfg.get("backend_type", l_cfg.get("backend_type", "unknown"))
            
            # Global Presets write to backend_config (b_cfg). Default settings live in llm_config (l_cfg).
            # We must check b_cfg first, then l_cfg, then the hardcoded fallback.
            _m_temp = b_cfg.get("temperature", l_cfg.get("temperature", 0.7))
            _m_ctx = b_cfg.get("num_ctx", l_cfg.get("num_ctx", 4096))
            _m_top_p = b_cfg.get("top_p", l_cfg.get("top_p", 0.9))
            _m_rep_pen = b_cfg.get("repeat_penalty", l_cfg.get("repeat_penalty", 1.1))
            _m_predict = b_cfg.get("num_predict", l_cfg.get("num_predict", 1024))
            _m_gpu = b_cfg.get("num_gpu", b_cfg.get("gpu_layers", 0))
            
            # Extra info from full_config
            full_config = full_config or {}
            ai_cfg = full_config.get("ai", {})
            _persona = b_cfg.get("active_personality", l_cfg.get("active_personality", ai_cfg.get("active_personality")))
            voice_cfg = full_config.get("voice", {})
            _tts_engine = voice_cfg.get("tts_engine", ai_cfg.get("tts_engine"))
            _tts_voice = voice_cfg.get("tts_voice", ai_cfg.get("tts_voice"))
            
            # Clean .yaml suffix on persona snapshot if present
            if isinstance(_persona, str) and _persona.endswith(".yaml"):
                _persona = _persona[:-5]

            # Create a structured dictionary
            info_dict = {
                "model": _m_name,
                "backend": _m_backend,
                "temperature": _m_temp,
                "num_ctx": _m_ctx,
                "top_p": _m_top_p,
                "repeat_penalty": _m_rep_pen,
                "num_predict": _m_predict,
                "num_gpu": _m_gpu,
                "persona": _persona,
                "tts_engine": _tts_engine,
                "tts_voice": _tts_voice
            }
            
            # Serialize to JSON string for database storage
            _model_info_str = json.dumps(info_dict)
            
            # Inject into LAST_PAYLOAD_INFO for the SSE trace_done event
            try:
                from hecos.core.llm.client import LAST_PAYLOAD_INFO
                LAST_PAYLOAD_INFO["model_info"] = _model_info_str
            except Exception:
                pass
        return _model_info_str

    @staticmethod
    def _resolve_tts_voice_label(ai_cfg: dict, voice_cfg: dict, engine: str, default_voice: str):
        """Resolves effective TTS preset or cloned reference name for tooltip display."""
        import os

        eng = (engine or "").lower()
        if not eng:
            return default_voice
        voice_overrides = ai_cfg.get("voice_overrides", {}) or {}
        if eng in ("xtts", "xtts2"):
            try:
                preset = voice_overrides.get("xtts_preset") or voice_cfg.get("xtts_preset") or ai_cfg.get("xtts_preset")
                if not preset:
                    from hecos.core.audio.device_manager import get_audio_config
                    curr = (get_audio_config().get("xtts", {}).get("current_preset", "") or "").strip()
                    if curr and curr != "default":
                        preset = curr
                if preset and preset != "default":
                    return preset
                speaker_wav = voice_overrides.get("xtts_speaker_wav") or voice_cfg.get("xtts_speaker_wav")
                if not speaker_wav:
                    from hecos.core.audio.device_manager import get_audio_config
                    speaker_wav = (get_audio_config().get("xtts", {}).get("speaker_wav", "") or "").strip()
                if speaker_wav:
                    return f"Clone: {os.path.splitext(os.path.basename(speaker_wav))[0]}"
            except Exception:
                pass
        elif eng in ("fish_speech", "fish"):
            try:
                preset = voice_overrides.get("fish_preset") or voice_cfg.get("fish_preset") or ai_cfg.get("fish_preset")
                if not preset:
                    from hecos.core.audio.device_manager import get_audio_config
                    preset = (get_audio_config().get("fish_speech", {}).get("current_preset", "") or "").strip()
                if preset and preset != "default":
                    return preset
                ref_audio = voice_overrides.get("fish_reference_audio") or voice_cfg.get("fish_reference_audio") or default_voice
                if not ref_audio:
                    from hecos.core.audio.device_manager import get_audio_config
                    ref_audio = (get_audio_config().get("fish_speech", {}).get("reference_audio", "") or "").strip()
                if ref_audio and ref_audio != "default":
                    return f"Clone: {os.path.splitext(os.path.basename(ref_audio))[0]}"
                if not ref_audio or ref_audio == "default":
                    return "Default Voice (Base)"
            except Exception:
                pass
        elif eng == "kokoro":
            try:
                preset = voice_overrides.get("kokoro_preset") or voice_cfg.get("kokoro_preset") or ai_cfg.get("kokoro_preset")
                if not preset:
                    from hecos.core.audio.device_manager import get_audio_config
                    curr = (get_audio_config().get("kokoro", {}).get("current_preset", "") or "").strip()
                    if curr and curr != "default":
                        preset = curr
                if preset and preset != "default":
                    return preset
                k_voice = voice_overrides.get("kokoro_voice") or voice_cfg.get("kokoro_voice") or default_voice
                if k_voice:
                    return os.path.splitext(os.path.basename(k_voice))[0]
            except Exception:
                pass
        return default_voice

    @staticmethod
    def enrich_model_info(
        raw_model_info=None,
        config=None,
        session_id=None,
        persona_name=None,
        trace_summary=None,
    ):
        """
        Ensures `model_info` always includes full model/preset/persona/generation parameters
        alongside optional `agent_trace` and usage metrics, returning `(json_str, info_dict)`.
        """
        cfg = config if isinstance(config, dict) else {}
        info_dict = {}
        if isinstance(raw_model_info, dict):
            info_dict = dict(raw_model_info)
        elif isinstance(raw_model_info, str) and raw_model_info.strip():
            try:
                parsed = json.loads(raw_model_info)
                if isinstance(parsed, dict):
                    info_dict = parsed
            except Exception:
                pass

        if not info_dict.get("model") and cfg:
            try:
                try:
                    from app.model_manager import ModelManager
                except ImportError:
                    from hecos.app.model_manager import ModelManager
                eff_backend, eff_model = ModelManager.get_effective_model_info(cfg)
                b_cfg = (cfg.get("backend", {}) or {}).get(eff_backend, {}).copy()
                if eff_model:
                    b_cfg["model"] = eff_model
                b_cfg["backend_type"] = eff_backend
                built_str = HistoryManager._build_model_info(b_cfg, cfg.get("llm", {}) or {}, cfg)
                if built_str:
                    built_dict = json.loads(built_str)
                    for k, v in built_dict.items():
                        info_dict.setdefault(k, v)
            except Exception:
                pass

        try:
            from hecos.core.global_presets.manager import get_active_soul_id
            if not info_dict.get("global_preset"):
                info_dict["global_preset"] = get_active_soul_id("global")
            if session_id and not info_dict.get("session_preset"):
                info_dict["session_preset"] = get_active_soul_id(session_id)
        except Exception:
            pass

        try:
            from hecos.core.llm.client import LAST_PAYLOAD_INFO
            if not info_dict.get("prompt_tokens") and LAST_PAYLOAD_INFO.get("prompt_tokens"):
                info_dict["prompt_tokens"] = LAST_PAYLOAD_INFO.get("prompt_tokens", 0)
            if not info_dict.get("completion_tokens") and LAST_PAYLOAD_INFO.get("completion_tokens"):
                info_dict["completion_tokens"] = LAST_PAYLOAD_INFO.get("completion_tokens", 0)
        except Exception:
            pass

        ai_cfg = cfg.get("ai", {}) or {}
        voice_cfg = cfg.get("voice", {}) or {}
        if not info_dict.get("persona"):
            raw_p = persona_name or ai_cfg.get("active_personality") or ""
            info_dict["persona"] = raw_p[:-5] if isinstance(raw_p, str) and raw_p.endswith(".yaml") else raw_p
        if not info_dict.get("backend") or info_dict.get("backend") == "unknown":
            btype = (cfg.get("backend", {}) or {}).get("type")
            if btype:
                info_dict["backend"] = btype
        if not info_dict.get("tts_engine"):
            info_dict["tts_engine"] = voice_cfg.get("tts_engine", ai_cfg.get("tts_engine"))
        if not info_dict.get("tts_voice"):
            info_dict["tts_voice"] = voice_cfg.get("tts_voice", ai_cfg.get("tts_voice"))
        info_dict["tts_voice"] = HistoryManager._resolve_tts_voice_label(
            ai_cfg, voice_cfg, info_dict.get("tts_engine"), info_dict.get("tts_voice")
        )

        if trace_summary:
            info_dict["agent_trace"] = trace_summary

        serialized = json.dumps(info_dict) if info_dict else None
        return serialized, info_dict
