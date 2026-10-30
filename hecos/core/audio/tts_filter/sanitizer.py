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
    Known issue: XTTS v2 sometimes vocalizes isolated period characters or ellipses as "punto"
    in Italian.
    
    IMPORTANT: We must NOT replace mid-text sentence periods ('. ') with commas,
    as that destroys sentence boundaries and causes pysbd to return a single massive
    block exceeding XTTS's 400-token architectural limit.
    Instead, collapse multiple dots to a single period and strip trailing dots.
    """
    # Replace multiple dots with a single dot
    text = re.sub(r'\.{2,}', '.', text)

    # Strip any trailing period at the very end of the text
    text = text.rstrip('. ')

    return text



def _is_fish_cloud() -> bool:
    try:
        from hecos.core.audio.device_manager import get_audio_config
        acfg = get_audio_config()
        fcfg = acfg.get("fish_speech", {})
        return bool(fcfg.get("api_key") and "api.fish.audio" in fcfg.get("api_url", ""))
    except Exception:
        return False


def sanitize_text(text: str, engine: str = None) -> str:
    """
    Applies filters to the TTS text based on current configuration.
    """
    if not text:
        return text

    config = get_filter_config()
    if not engine:
        engine = _get_active_engine()
    
    # 0. Fish Speech Expressive Tags Handling (S2-Pro & S2.1-Pro)
    fish_tags = []
    if engine in ("fish_speech", "fish") or re.search(r'\[(whisper|laughing|excited|calm|sigh|surprised|angry|sad|dramatic)\]', text, re.IGNORECASE):
        # Both Fish Speech S2-Pro locally and S2.1-Pro Cloud natively parse bracket emotion tags
        def _save_tag(m):
            fish_tags.append(m.group(0))
            return f"\uE000FISHTAG{len(fish_tags)-1}\uE001"
        text = re.sub(r'\[[a-zA-Z\s_-]+\]', _save_tag, text)

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
        if engine in ("xtts2", "xtts"):
            text = _sanitize_for_xtts(text)

    # Restore protected Fish Speech tags
    if fish_tags:
        for idx, tag in enumerate(fish_tags):
            text = text.replace(f"\uE000FISHTAG{idx}\uE001", tag)

    # Clean up double spaces
    text = re.sub(r'\s+', ' ', text)
    # Fix detached punctuation (e.g. "word ," -> "word,")
    text = re.sub(r'\s+([.,!?;:])', r'\1', text)
    
    return text.strip()
