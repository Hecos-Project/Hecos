import re
import json
import unicodedata

# Cache to avoid disk reads on every sentence
_config_cache = None

def should_filter(conf_val, mode):
    """
    Checks if a filter should be applied based on its target setting.
    conf_val can be a bool (legacy) or a string ('voice', 'text', 'both', 'none').
    mode is either 'voice' or 'text'.
    """
    if isinstance(conf_val, bool):
        # Legacy boolean logic: if it's True, we apply to both to be safe
        return conf_val
    if not isinstance(conf_val, str):
        return False
        
    val = conf_val.lower()
    if val in ("both", "all"):
        return True
    if val == mode:
        return True
    return False

def apply_custom_filters(text, conf, mode):
    """Applies the custom filters list from the config, respecting the target."""
    if not text:
        return text
    
    # 1. Legacy string replacements
    replacements = conf.get("custom_replacements", {})
    if isinstance(replacements, dict):
        for target, replacement in replacements.items():
            text = text.replace(target, replacement)
            
    # 2. New custom filter objects
    custom_filters = conf.get("custom_filters", [])
    if isinstance(custom_filters, list):
        for cf in custom_filters:
            if not isinstance(cf, dict):
                continue
            f_target = cf.get("target", "both")
            if should_filter(f_target, mode):
                f_find = cf.get("find", "")
                if f_find:
                    f_replace = str(cf.get("replace", ""))
                    # Use case-insensitive regex replacement for user convenience
                    pattern = re.compile(re.escape(f_find), re.IGNORECASE)
                    # Using lambda to avoid issues with regex backreferences in standard strings
                    text = pattern.sub(lambda m: f_replace, text)
    return text

def load_filter_config():
    global _config_cache
    if _config_cache is None:
        try:
            import os
            # Calcola la root (hecos/core/processing -> ../../../)
            root = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
            path = os.path.join(root, "hecos", "config", "data", "system.yaml")
            if os.path.exists(path):
                import yaml
                with open(path, "r", encoding="utf-8") as f:
                    full_config = yaml.safe_load(f) or {}
                    _config_cache = full_config.get("filters", {})
            else:
                _config_cache = {}
        except Exception:
            return {}
    return _config_cache or {}

def reset_cache():
    """Clears cache to force a reload on next use, useful after panel updates."""
    global _config_cache
    _config_cache = None

def remove_think_tags(text):
    """
    Removes <think>...</think> blocks produced by reasoning models (Qwen, DeepSeek-R1, etc.).
    Supports case-insensitive tags and multiline blocks.
    """
    if not text:
        return text
    # Removes <think>...</think> blocks (case-insensitive, multiline)
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL | re.IGNORECASE)
    # Removes any open <think> without closure (truncated response)
    text = re.sub(r'<think>.*$', '', text, flags=re.DOTALL | re.IGNORECASE)
    return text.strip()

def remove_emoji(text):
    """
    Removes emojis and other special characters not supported by speech synthesis.
    """
    # Filter non-printable characters and emojis
    # Keep only letters, numbers, basic punctuation, and spaces
    pattern = re.compile(r'[^\x00-\x7F\u00C0-\u017F\s\.,!?;:\'"\(\)\[\]\{\}]')
    clean_text = pattern.sub('', text)
    return clean_text

def clean_for_video(text):
    """
    Sanitizes text for safe terminal output on Windows.
    Converts non-cp1252 characters (emojis, extended unicode) to '?' instead of crashing.
    This is the safe path for ALL text displayed on screen.
    """
    if not text:
        return ""
    # Remove <think> tags from reasoning models (Qwen, DeepSeek-R1, etc.)
    text = remove_think_tags(text)
    if not text:
        return ""
    
    # Check user-configured text filters for visible text
    conf = load_filter_config()
    
    # Apply custom filters targeting 'text' or 'both'
    text = apply_custom_filters(text, conf, mode="text")
    
    # 1. Removes text between asterisks
    if should_filter(conf.get("remove_asterisks", "both"), "text"):
        text = re.sub(r"\*.*?\*", "", text)

    # 2. Removes text between round brackets
    if should_filter(conf.get("remove_round_brackets", "voice"), "text"):
        text = re.sub(r"\(.*?\)", "", text)

    # 3. Handle square brackets
    if should_filter(conf.get("remove_square_brackets", "none"), "text"):
        text = re.sub(r"\[.*?\]", "", text)
        
    try:
        # Encode in cp1252 with 'replace' (replaces unsupported characters with '?')
        # then decode back to a Python string - the terminal can now always print it
        return text.encode('cp1252', errors='replace').decode('cp1252')
    except Exception:
        # Ultra-safe fallback: remove everything non-pure-ASCII
        return text.encode('ascii', errors='replace').decode('ascii')

def safe_print(*args, **kwargs):
    """
    Safe print() version for Windows terminals.
    Automatically uses clean_for_video() on each string argument.
    """
    import sys
    safe_args = [clean_for_video(str(a)) if isinstance(a, str) else a for a in args]
    try:
        print(*safe_args, **kwargs)
    except Exception:
        # Ultimate fallback: pure ASCII
        plain = ' '.join(str(a).encode('ascii', errors='replace').decode('ascii') for a in args)
        sys.stdout.write(plain + '\n')
        sys.stdout.flush()

def clean_for_voice(text):
    if not text:
        return ""

    conf = load_filter_config()

    # 0. Remove <think> tags from reasoning models (Qwen, DeepSeek-R1, etc.)
    text = remove_think_tags(text)
    if not text:
        return ""

    # 1b. Remove emojis and special characters
    text = remove_emoji(text)

    # 1. Custom and dynamic filters targeting 'voice'
    text = apply_custom_filters(text, conf, mode="voice")

    # 2. Removes text between asterisks
    if should_filter(conf.get("remove_asterisks", "both"), "voice"):
        text = re.sub(r"\*.*?\*", "", text)

    # 3. Removes text between round brackets
    if should_filter(conf.get("remove_round_brackets", "voice"), "voice"):
        text = re.sub(r"\(.*?\)", "", text)

    # 4. Handle square brackets
    if should_filter(conf.get("remove_square_brackets", "none"), "voice"):
        text = re.sub(r"\[.*?\]", "", text)
    else:
        text = text.replace("[", "").replace("]", "")

    # 5. Removes markdown (bold, italic)
    if conf.get("remove_markdown", True):
        text = re.sub(r'\*\*.*?\*\*', '', text)
        text = re.sub(r'__.*?__', '', text)
        text = re.sub(r'\*.*?\*', '', text)

    # 6. Double space cleanup
    text = re.sub(r'\s+', ' ', text).strip()

    return text
