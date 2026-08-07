import os
import re
import glob
import platform

# Paths and Constants
CWD = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PIPER_DIR = os.path.join(CWD, "bin", "piper")
PIPER_REPO_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0"
SYSTEM_CONFIG_PATH = os.path.join(CWD, "hecos", "config", "data", "system.yaml")
AUDIO_CONFIG_PATH = os.path.join(CWD, "hecos", "config", "data", "audio.yaml")
LOGO_PATH = os.path.join(CWD, "hecos", "assets", "Hecos_Logo_SQR_NBG_LogoOnly.png")

def _find_tray_dir():
    """
    Locate the Hecos-Tray directory intelligently.
    Handles: exact name, versioned suffix (Hecos-Tray-1.5.3), any drive root.
    Returns (tray_path, is_versioned) where is_versioned=True means folder has a version suffix.
    """
    _root_drive = os.path.splitdrive(CWD)[0] or "C:"

    # 1. Exact canonical name
    canonical = os.path.join(_root_drive, os.sep, "Hecos-Tray")
    if os.path.isfile(os.path.join(canonical, "tray", "version")):
        return canonical, False

    # 2. Wildcard: Hecos-Tray-* (GitHub versioned download)
    pattern = os.path.join(_root_drive, os.sep, "Hecos-Tray-*")
    matches = sorted(glob.glob(pattern))
    for candidate in matches:
        if os.path.isfile(os.path.join(candidate, "tray", "version")):
            return candidate, True   # found but has version suffix

    return None, False  # not found

TRAY_DIR, TRAY_DIR_VERSIONED = _find_tray_dir()
TRAY_DIR_CANONICAL = os.path.join(os.path.splitdrive(CWD)[0] or "C:", os.sep, "Hecos-Tray")


VOICE_MAP = {
    "en": {"female": "en_US-lessac-low", "male": "en_US-bryce-medium"},
    "it": {"female": "it_IT-paola-medium", "male": "it_IT-riccardo-x_low"}
}

def safe_replace_yaml(filepath, key, value):
    if not os.path.exists(filepath):
        return False
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    safe_value = str(value).replace('\\', '\\\\')
    # Match key at start of line OR with spaces (handles nested yaml)
    pattern = rf'(?m)^(\s*){key}:\s*.*$'
    replacement = rf'\1{key}: {safe_value}'
    
    new_content = re.sub(pattern, replacement, content)
    
    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True
    
    # If content already matches, check if the key is present
    if re.search(pattern, content):
        return True # Considered successful if already set to target
        
    return False

def get_current_system_lang():
    if os.path.exists(SYSTEM_CONFIG_PATH):
        with open(SYSTEM_CONFIG_PATH, 'r', encoding='utf-8') as f:
            m = re.search(r'language:\s*(.*)', f.read())
            if m: return m.group(1).strip().lower()
    return "en"
