"""
MODULE: Logical Processor - Hecos v2.5
DESCRIPTION: The 'execution engine'. Transforms AI thought into real actions 
via plugins and filters text for speech synthesis.

Facade module. Tool dispatching logic is in tool_dispatcher.py.
"""
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

def configure(new_config):
    """Receives configuration from Main and stores it for Brain calls."""
    global current_config
    current_config = new_config
    logger.info("[PROCESSOR] Hardware configuration synchronized.")

def process_exchange(user_text, voice_status, sm=None):
    """Manages the entire chain: AI -> Plugin -> Cleaning -> Response.
    NOW REFACTORED TO USE THE AGENTIC LOOP."""
    logger.info(f"[PROCESSOR] Input received (length: {len(user_text)}). Delegating to Agentic Loop.")
    
    from hecos.core.agent.loop import AgentExecutor
    
    executor = AgentExecutor(config=current_config, state_manager=sm)
    video_response, clean_voice = executor.run_agentic_loop(user_text, voice_status=voice_status)
    return video_response, clean_voice


# Tokens that must survive tag cleanup (intercepted by the browser JS)
_PRESERVED_TOKENS = ["[CAMERA_SNAPSHOT_REQUEST]"]

def clean_final_output(base_text, tool_results, raw_response_obj, voice_status=False):
    """Formats the final text for display and TTS after all loops are complete."""
    import re as _re
    # Temporarily protect special tokens from regex stripping
    _placeholders = {}
    for i, tok in enumerate(_PRESERVED_TOKENS):
        placeholder = f"__PRESERVED_{i}__"
        _placeholders[placeholder] = tok
        base_text = base_text.replace(tok, placeholder)
    
    # Protect [[IMG:...]] tags from the regex below
    _img_tags = _re.findall(r'\[\[IMG:[^\]]+\]\]', base_text)
    for j, img_tag in enumerate(_img_tags):
        marker = f"__IMG_{j}__"
        _placeholders[marker] = img_tag
        base_text = base_text.replace(img_tag, marker, 1)
    
    # Extract tags (for UI rendering if legacy tags were used instead of native functions)
    base_video = _re.sub(r'\[.*?:.*?\]', '', base_text).strip()
    base_video = _re.sub(r'\[.*?\]', '', base_video).strip()
    
    # Restore preserved tokens and IMG tags
    for placeholder, tok in _placeholders.items():
        base_video = base_video.replace(placeholder, tok)
    
    if not base_video:
        if tool_results:
            base_video = f"✅ {translator.t('command_executed_info', info='Tools Eseguiti')}"
        else:
            base_video = translator.t('model_no_response_error')
    
    video_response = filtri.clean_for_video(base_video)
    
    clean_voice_text = ""
    if voice_status:
        # We use base_video so Hecos speaks only her intention, not the raw JSON/logs.
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
                        video_response += f"\n\n{img_tag}"
            else:
                # The raw tool output appending logic has been moved to loop.py
                # so that the appended outputs are saved to the chat history database.
                pass
                
    return video_response, clean_voice_text
