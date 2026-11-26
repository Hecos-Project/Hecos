"""
MODULE: Logical Processor - Hecos v2.5
DESCRIPTION: The 'execution engine'. Transforms AI thought into real actions 
via plugins and filters text for speech synthesis.

Facade module. Tool dispatching logic is in tool_dispatcher.py.
"""
import copy
from hecos.core.processing import filtri
from hecos.core.logging import logger
from hecos.core.i18n import translator

# Import the new tool dispatcher
from hecos.core.processing.tool_dispatcher import (
    extract_and_execute_tools,
    TAG_MAPPING,
    BLACKLIST
)

# Global variable to hold hardware parameters
current_config = {}


def _build_cli_runtime_config(base_config):
    """Builds an isolated per-turn config copy for CLI execution.
    - Prevents per-turn flags (_turn_*) from leaking across CLI turns.
    - Keeps CLI strictly decoupled from WebUI Global Presets (model + soul + TTS only).
    - Applies explicit backend.ollama.enable_thinking if set, or disables thinking when
      num_predict <= 2048 to prevent thinking-token starvation/truncation on Gemma 4 / Qwen.
    """
    cfg = copy.deepcopy(base_config) if isinstance(base_config, dict) else {}
    for k in list(cfg.keys()):
        if str(k).startswith("_turn_"):
            cfg.pop(k, None)

    ai_cfg = cfg.setdefault("ai", {})
    if isinstance(ai_cfg, dict):
        ai_cfg["active_global_preset"] = ""

    pctrl = cfg.setdefault("payload_control", {})
    if isinstance(pctrl, dict):
        pctrl.setdefault("send_tools", True)
        pctrl.setdefault("send_personality", True)
        pctrl.setdefault("send_memory", True)

        backend_cfg = cfg.get("backend") or {}
        btype = str(backend_cfg.get("type") or "ollama").lower()
        if btype == "hybrid":
            btype = str(backend_cfg.get("active_model_source") or "ollama").lower()
        if btype == "ollama":
            ollama_cfg = backend_cfg.get("ollama") or {}
            explicit_think = pctrl.get("enable_thinking")
            if explicit_think is None:
                explicit_think = ollama_cfg.get("enable_thinking")
            if explicit_think is not None:
                pctrl["enable_thinking"] = bool(explicit_think)
            else:
                try:
                    n_pred = int(ollama_cfg.get("num_predict") or 0)
                except (TypeError, ValueError):
                    n_pred = 0
                if 0 < n_pred <= 2048:
                    pctrl["enable_thinking"] = False
                    logger.info(
                        f"[PROCESSOR] CLI auto-guard: enable_thinking=False for Ollama "
                        f"(num_predict={n_pred} <= 2048 avoids thinking-token truncation; use '/think on' to force)."
                    )

    return cfg


def configure(new_config):
    """Receives configuration from Main and stores it for Brain calls."""
    global current_config
    current_config = new_config
    logger.info("[PROCESSOR] Hardware configuration synchronized.")


def process_exchange(
    user_text,
    voice_status,
    sm=None,
    config_manager=None,
    cancel_event=None,
    turn_id=None,
    trace_callback=None,
    session_id=None,
):
    """Manages the entire chain: AI -> Plugin -> Cleaning -> Response.
    NOW REFACTORED TO USE THE AGENTIC LOOP."""
    logger.info(f"[PROCESSOR] Input received (length: {len(user_text)}). Delegating to Agentic Loop.")

    from hecos.core.agent.loop import AgentExecutor

    if config_manager is not None and getattr(config_manager, "config", None):
        base_cfg = config_manager.config
        turn_cfg = _build_cli_runtime_config(base_cfg)
    elif current_config and isinstance(current_config, dict) and current_config.get("backend"):
        turn_cfg = _build_cli_runtime_config(current_config)
    else:
        import sys as _sys
        sys_mgr = getattr(_sys, "hecos_config_manager", None)
        raw_base = getattr(sys_mgr, "config", None) if sys_mgr is not None else None
        if not raw_base:
            from hecos.core.llm import brain as _brain
            raw_base = _brain.load_config() or {}
        try:
            from hecos.config.session_config_manager import merge_session_config
            turn_cfg = merge_session_config(raw_base, session_id=session_id)
        except Exception:
            turn_cfg = _build_cli_runtime_config(raw_base)
        if config_manager is None and sys_mgr is not None:
            config_manager = sys_mgr

    executor = AgentExecutor(
        config=turn_cfg,
        config_manager=config_manager,
        state_manager=sm,
        trace_callback=trace_callback,
        session_id=session_id,
        cancel_event=cancel_event,
        turn_id=turn_id,
    )
    video_response, clean_voice = executor.run_agentic_loop(user_text, voice_status=voice_status)
    return video_response, clean_voice


# Tokens that must survive tag cleanup (intercepted by the browser JS or used as Markdown plan badges)
_PRESERVED_TOKENS = [
    "[CAMERA_SNAPSHOT_REQUEST]",
    "[NEW]",
    "[MODIFY]",
    "[DELETE]",
    "[RENAME]",
    "[TEST]",
    "[x]",
    "[X]",
    "[NOTE]",
    "[TIP]",
    "[IMPORTANT]",
    "[WARNING]",
    "[CAUTION]",
]

# Slash commands emitted by the LLM that should be stripped from visible/voice output once executed
_EXECUTED_SLASH_CMD_RE = (
    r'(?m)^\s*/(?:img|image|photo|foto|search|netsearch|cerca|websearch|dark|onion|tor_search|'
    r'media|find_media|videos|video|cerca_video|images|immagini|foto_web|cerca_immagini|'
    r'files|file|cerca_file|fetch|read_url|osint|whois_user|'
    r'streams|live|tv|iptv|radio|fm|webcam|cam|canale|channel|remote|canali|channels|lista|'
    r'pdf|makepdf|documento|generate_pdf|DOCS__generate_pdf|modify_document|DOCS__modify_document|'
    r'list_documents|DOCS__list_documents|optimize_layout|DOCS__optimize_layout)\b[^\r\n]*(?:\r?\n)?'
)


def _format_igen_alert_blockquote(alert_text: str) -> str:
    """Formats a raw [[IGEN_ALERT]] body into a clean Markdown blockquote."""
    lines = [line.rstrip() for line in (alert_text or "").strip().splitlines()]
    quoted = [f"> {line}" if line.strip() else ">" for line in lines]
    return "\n".join(quoted)


def clean_final_output(base_text, tool_results, raw_response_obj, voice_status=False):
    """Formats the final text for display and TTS after all loops are complete."""
    import re as _re
    if not isinstance(base_text, str):
        base_text = str(base_text or "")

    # Collect any [[IGEN_ALERT]]...[[/IGEN_ALERT]] diagnostic blocks from base_text and tool_results
    _collected_alerts = []
    for match in _re.findall(r'\[\[IGEN_ALERT\]\](.*?)\[\[/IGEN_ALERT\]\]', base_text, flags=_re.DOTALL):
        clean_m = match.strip()
        if clean_m and clean_m not in _collected_alerts:
            _collected_alerts.append(clean_m)

    # Collect [[STREAM_STATUS]]...[[/STREAM_STATUS]] blocks so they render in UI without being spoken by TTS
    _collected_stream_badges = []
    for match in _re.findall(r'\[\[STREAM_STATUS\]\](.*?)\[\[/STREAM_STATUS\]\]', base_text, flags=_re.DOTALL):
        clean_s = match.strip()
        if clean_s and clean_s not in _collected_stream_badges:
            _collected_stream_badges.append(clean_s)

    # Collect [[IGEN_META]] / "> **[Image Gen Config]** ..." and SwarmUI auto-start lines
    # so they are ALWAYS displayed in chat when enabled (even on early-termination fast path)
    # without being mangled by asterisk/bracket filters or read aloud by TTS.
    _collected_igen_meta = []
    _igen_meta_re = _re.compile(
        r'(?m)^\s*>\s*(?:🖥️\s*)?\*\*\[(?:Image Gen Config|SwarmUI Auto-Start)\]\*\*[^\r\n]*$'
    )
    for m_line in _igen_meta_re.findall(base_text):
        clean_meta = m_line.strip()
        if clean_meta and clean_meta not in _collected_igen_meta:
            _collected_igen_meta.append(clean_meta)

    if tool_results:
        for r in tool_results:
            out = r.get('output', '')
            if out and isinstance(out, str):
                for match in _re.findall(r'\[\[IGEN_ALERT\]\](.*?)\[\[/IGEN_ALERT\]\]', out, flags=_re.DOTALL):
                    clean_m = match.strip()
                    if clean_m and clean_m not in _collected_alerts:
                        _collected_alerts.append(clean_m)
                for m_line in _igen_meta_re.findall(out):
                    clean_meta = m_line.strip()
                    if clean_meta and clean_meta not in _collected_igen_meta:
                        _collected_igen_meta.append(clean_meta)

    # Strip raw [[IGEN_ALERT]] / [[STREAM_STATUS]] wrappers and Image Gen metadata lines from base_text before bracket regex & TTS
    base_text = _re.sub(r'\[\[IGEN_ALERT\]\].*?\[\[/IGEN_ALERT\]\]', '', base_text, flags=_re.DOTALL).strip()
    base_text = _re.sub(r'\[\[STREAM_STATUS\]\].*?\[\[/STREAM_STATUS\]\]', '', base_text, flags=_re.DOTALL).strip()
    base_text = _igen_meta_re.sub('', base_text).strip()

    # Strip executed slash command lines and inline MODULE__method(...) calls when tools were executed
    if tool_results:
        base_text = _re.sub(_EXECUTED_SLASH_CMD_RE, '', base_text).strip()
        try:
            from hecos.core.processing.parsers.legacy_tag_parser import strip_module_call_syntax
            base_text = strip_module_call_syntax(base_text)
        except Exception:
            pass

    # Temporarily protect special tokens from regex stripping
    _placeholders = {}
    for i, tok in enumerate(_PRESERVED_TOKENS):
        placeholder = f"__PRESERVED_{i}__"
        _placeholders[placeholder] = tok
        base_text = base_text.replace(tok, placeholder)
    
    # Protect fenced and inline code blocks first so Python/JS brackets & slices are never corrupted
    _code_blocks = _re.findall(r'```[\s\S]*?```|`[^`\r\n]+`', base_text)
    for c_idx, c_block in enumerate(_code_blocks):
        c_marker = f"__CODEBLOCK_{c_idx}__"
        _placeholders[c_marker] = c_block
        base_text = base_text.replace(c_block, c_marker, 1)

    # Protect [[IMG:...]] tags from the regex below
    _img_tags = _re.findall(r'\[\[IMG:[^\]]+\]\]', base_text)
    for j, img_tag in enumerate(_img_tags):
        marker = f"__IMG_{j}__"
        _placeholders[marker] = img_tag
        base_text = base_text.replace(img_tag, marker, 1)

    # Protect [[HSEARCH:...]] and [[HMEDIA:...]] tags from regex stripping
    _search_tags = _re.findall(r'\[\[H(?:SEARCH|MEDIA):[^\]]+\]\]', base_text)
    for k, s_tag in enumerate(_search_tags):
        marker = f"__HSEARCH_{k}__"
        _placeholders[marker] = s_tag
        base_text = base_text.replace(s_tag, marker, 1)

    # Protect Markdown links and images [label](url) / ![alt](url) so bracket tag stripping never breaks them
    _md_links = _re.findall(r'!?\[[^\]]*\]\([^\)]+\)', base_text)
    for m, md_link in enumerate(_md_links):
        marker = f"__MDLINK_{m}__"
        _placeholders[marker] = md_link
        base_text = base_text.replace(md_link, marker, 1)
    
    # Strip legacy tool tags (e.g. [SYSTEM: time], [DOCS: ...]) while leaving non-module brackets untouched
    base_video = _re.sub(r'\[[A-Za-z][A-Za-z0-9_]*:[^\]]*?\]', '', base_text, flags=_re.DOTALL).strip()
    base_video = _re.sub(r'\[[A-Za-z][A-Za-z0-9_]*\]', '', base_video).strip()

    # Strip any orphan/hallucinated Live Stream status lines or dangling > 📺 blockquotes
    # (genuine stream status badges are collected via [[STREAM_STATUS]] and appended below)
    base_video = _re.sub(
        r'(?m)^\s*(?:>\s*)?(?:📺|⏹️|⏯️)\s*(?:Tuned to[^\r\n]*|Live Stream stopped[^\r\n]*|Playback (?:paused|resumed)[^\r\n]*)?\s*(?:\r?\n)?',
        '',
        base_video,
    ).strip()
    base_video = _re.sub(r'(?m)^\s*>\s*(?:\r?\n|$)', '', base_video).strip()
    base_video = _re.sub(r'\n{3,}', '\n\n', base_video).strip()
    
    # Restore preserved tokens, IMG tags, HSEARCH tags, and Markdown links
    for placeholder, tok in _placeholders.items():
        base_video = base_video.replace(placeholder, tok)
    
    if not base_video:
        if _collected_alerts:
            base_video = ""
        elif tool_results:
            base_video = f"✅ {translator.t('command_executed_info', info='Tools Executed')}"
        else:
            base_video = translator.t('model_no_response_error')
    
    video_response = filtri.clean_for_video(base_video) if base_video else ""
    
    clean_voice_text = ""
    if voice_status and base_video:
        # We use base_video so Hecos speaks only her intention, not the raw JSON/logs/media tags.
        clean_voice_text = filtri.clean_for_voice(base_video)
        
    if tool_results:
        for r in tool_results:
            out = r.get('output', '')
            if not out:
                continue
            # If this is an image generation result, extract only the [[IMG:]] tag to show
            img_tags_in_out = _re.findall(r'\[\[IMG:[^\]]+\]\]', out)
            if img_tags_in_out:
                for img_tag in img_tags_in_out:
                    if img_tag not in video_response:
                        video_response = f"{video_response}\n\n{img_tag}".strip()

    # Append Image Gen Config metadata lines (when 'Show Config in Chat' is enabled) — UI only, never spoken
    if _collected_igen_meta:
        for meta_line in _collected_igen_meta:
            if meta_line not in video_response:
                video_response = f"{video_response}\n\n{meta_line}".strip()

    # Append any diagnostic [[IGEN_ALERT]] or verified [[STREAM_STATUS]] banners as formatted blockquotes
    if _collected_alerts:
        for alert_body in _collected_alerts:
            formatted_block = _format_igen_alert_blockquote(alert_body)
            if formatted_block and formatted_block not in video_response:
                video_response = f"{video_response}\n\n{formatted_block}".strip()

    if _collected_stream_badges:
        for badge_body in _collected_stream_badges:
            formatted_badge = _format_igen_alert_blockquote(badge_body)
            if formatted_badge and formatted_badge not in video_response:
                video_response = f"{video_response}\n\n{formatted_badge}".strip()
                
    return video_response, clean_voice_text
