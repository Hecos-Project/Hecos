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
        
        if not is_error and save_history:
            # Snapshot the clean persona name so avatar stays correct even if user changes personality later
            clean_persona = personality_name.replace(".yaml", "") if personality_name else "Hecos_System_Soul"
            brain_interface.save_message("user", user_text, config=config, user_id=user_id, session_id=session_id, sender_tab_id=sender_tab_id)
            
            # Build generation parameters JSON string for UI Tooltip and History
            llm_config = config.get("llm", {})
            _model_info_str = HistoryManager._build_model_info(backend_config, llm_config)
            
            # Structured response management (String or Message with tool_calls)
            if isinstance(response, str):
                logger.debug("HistoryManager", f"Response received from backend: {len(response)} characters")
                # Sanitize: if the model returned raw JSON (e.g. Ollama fallback format),
                # save only the clean text to DB so history doesn't store raw JSON.
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
    def _build_model_info(backend_config, llm_config):
        _model_info_str = None
        if backend_config or llm_config:
            b_cfg = backend_config or {}
            l_cfg = llm_config or {}
            
            _m_name = b_cfg.get("model", "unknown")
            
            # Global Presets write to backend_config (b_cfg). Default settings live in llm_config (l_cfg).
            # We must check b_cfg first, then l_cfg, then the hardcoded fallback.
            _m_temp = b_cfg.get("temperature", l_cfg.get("temperature", 0.7))
            _m_ctx = b_cfg.get("num_ctx", l_cfg.get("num_ctx", 4096))
            _m_top_p = b_cfg.get("top_p", l_cfg.get("top_p", 0.9))
            _m_rep_pen = b_cfg.get("repeat_penalty", l_cfg.get("repeat_penalty", 1.1))
            _m_predict = b_cfg.get("num_predict", l_cfg.get("num_predict", 1024))
            _m_gpu = b_cfg.get("num_gpu", b_cfg.get("gpu_layers", 0))
            
            # Create a structured dictionary
            info_dict = {
                "model": _m_name,
                "temperature": _m_temp,
                "num_ctx": _m_ctx,
                "top_p": _m_top_p,
                "repeat_penalty": _m_rep_pen,
                "num_predict": _m_predict,
                "num_gpu": _m_gpu
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
