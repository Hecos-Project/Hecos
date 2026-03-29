import re
import json
import unicodedata

# Cache to avoid disk reads on every sentence
_config_cache = None

def load_filter_config():
    global _config_cache
    if _config_cache is None:
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                full_config = json.load(f)
                _config_cache = full_config.get("filters", {
                    "remove_asterisks": True,
                    "remove_round_brackets": True,
                    "remove_square_brackets": False,
                    "custom_replacements": {}
                })
        except Exception:
            return {}
    return _config_cache

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

    # 1. Custom replacements
    replacements = conf.get("custom_replacements", {})
    for target, replacement in replacements.items():
        text = text.replace(target, replacement)

    # 2. Removes text between asterisks
    if conf.get("remove_asterisks", True):
        text = re.sub(r"\*.*?\*", "", text)

    # 3. Removes text between round brackets
    if conf.get("remove_round_brackets", True):
        text = re.sub(r"\(.*?\)", "", text)

    # 4. Handle square brackets
    if conf.get("remove_square_brackets", False):
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