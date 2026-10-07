import re
from .config import get_filter_config

# Common LLM error patterns
LLM_ERROR_PATTERNS = [
    r"\[Error:.*?\]",
    r"System Exception.*",
    r"I am an AI, I cannot.*",
    r"As an AI language model,.*"
]


def _get_active_engine() -> str:
    """Returns the currently active TTS engine name."""
    try:
        from hecos.core.audio.device_manager import get_audio_config
        acfg = get_audio_config()
        return acfg.get("active_engine", "piper")
    except Exception:
        return "piper"


def _sanitize_for_xtts(text: str) -> str:
    """
    XTTS2-specific sanitization.
    Known issue: XTTS v2 sometimes vocalizes the period character as "punto"
    in Italian (and similar artifacts in other languages). This is a documented
    model limitation in Coqui's issue tracker.
    
    Fix: replace sentence-ending periods with commas (which produce a natural 
    pause but are never vocalized), and strip the very last period entirely.
    """
    # Replace ". " (mid-text sentence endings) with ", " — comma gives the
    # same pause cue to XTTS without being read aloud
    text = re.sub(r'\.\s+', ', ', text)

    # Strip any trailing period at the very end of the text
    text = text.rstrip('.')

    return text


def sanitize_text(text: str) -> str:
    """
    Applies filters to the TTS text based on current configuration.
    """
    if not text:
        return text

    config = get_filter_config()
    
    # 1. Apply custom replacements first
    for item in config.get("custom_replacements", []):
        target = item.get("target", "")
        replacement = item.get("replacement", "")
        if target:
            # case insensitive replacement
            pattern = re.compile(re.escape(target), re.IGNORECASE)
            text = pattern.sub(replacement, text)
            
    # 2. Remove LLM error patterns
    if config.get("remove_llm_errors", True):
        for pattern in LLM_ERROR_PATTERNS:
            text = re.sub(pattern, " ", text, flags=re.IGNORECASE)
            
    # 3. Remove/reduce punctuation (useful for XTTS)
    if config.get("remove_punctuation", False):
        # Remove asterisks and markdown symbols completely
        text = re.sub(r'[*~`]', '', text)
        # Replace multiple dots with a single dot to avoid XTTS glitching
        text = re.sub(r'\.{2,}', '.', text)
        # Clean up other weird symbols that cause issues
        text = re.sub(r'[<>]', '', text)

    # 4. XTTS2-specific: fix period vocalization ("punto" bug)
    if config.get("xtts_fix_periods", True):
        engine = _get_active_engine()
        if engine in ("xtts2", "xtts"):
            text = _sanitize_for_xtts(text)

    # Clean up double spaces
    text = re.sub(r'\s+', ' ', text)
    # Fix detached punctuation (e.g. "word ," -> "word,")
    text = re.sub(r'\s+([.,!?;:])', r'\1', text)
    
    return text.strip()
