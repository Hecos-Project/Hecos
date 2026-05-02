import os
import re

# Paths and Constants
CWD = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PIPER_DIR = os.path.join(CWD, "bin", "piper")
PIPER_REPO_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0"
SYSTEM_CONFIG_PATH = os.path.join(CWD, "hecos", "config", "data", "system.yaml")
AUDIO_CONFIG_PATH = os.path.join(CWD, "hecos", "config", "data", "audio.yaml")
LOGO_PATH = os.path.join(CWD, "hecos", "assets", "Hecos_Logo_NBG.png")

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
