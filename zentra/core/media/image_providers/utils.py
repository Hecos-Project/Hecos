import os
import uuid
import urllib.parse
import datetime

try:
    from zentra.core.logging import logger
except ImportError:
    class _Logger:
        def info(self, *a): print("[IMGPROVIDER]", *a)
        def error(self, *a): print("[IMGPROVIDER ERROR]", *a)
        def debug(self, *a): pass
    logger = _Logger()
# zentra/core/media/image_providers/utils.py -> ../../../ is zentra/
from zentra.core.constants import IMAGES_DIR, LOGS_DIR
# NOTE: IMAGES_DIR now points to zentra/media/images (centralized media)
# NOTE: SNAPSHOTS_DIR now points to zentra/media/screenshots (centralized media)

def log_debug(msg: str):
    log_file = os.path.join(LOGS_DIR, "image_gen_debug.txt")
    now = datetime.datetime.now().strftime("%H:%M:%S")
    try:
        os.makedirs(LOGS_DIR, exist_ok=True)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{now}] {msg}\n")
    except Exception:
        pass

def save_image_bytes(data: bytes, ext: str = "jpg", prompt: str = "") -> str:
    """
    Save raw image bytes and return filename.
    Adds creation date and prompt snippet to filename.
    Saves full prompt and timestamp in a sidecar .txt file.
    """
    import re
    os.makedirs(IMAGES_DIR, exist_ok=True)
    
    # 1. Generate descriptive filename
    now = datetime.datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    
    # Clean prompt for filename (limit to 50 chars, alnum only)
    safe_prompt = re.sub(r'[^a-zA-Z0-9]', '_', prompt[:50]).strip('_')
    if not safe_prompt:
        safe_prompt = "generation"
    
    filename = f"gen_{timestamp}_{safe_prompt}.{ext}"
    path = os.path.join(IMAGES_DIR, filename)
    
    # Check for collisions (rare with timestamp but possible)
    if os.path.exists(path):
        filename = f"gen_{timestamp}_{uuid.uuid4().hex[:4]}_{safe_prompt}.{ext}"
        path = os.path.join(IMAGES_DIR, filename)

    # 2. Save image
    with open(path, "wb") as f:
        f.write(data)
        
    # 3. Save sidecar metadata (.txt)
    try:
        meta_filename = filename.rsplit('.', 1)[0] + ".txt"
        meta_path = os.path.join(IMAGES_DIR, meta_filename)
        with open(meta_path, "w", encoding="utf-8") as f:
            f.write(f"ZENTRA IMAGE METADATA\n")
            f.write(f"=====================\n")
            f.write(f"Date: {now.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Prompt: {prompt}\n")
    except Exception as e:
        logger.error(f"[ImageEngine] Failed to save metadata: {e}")

    return filename

def get_proxies(provider: str = "") -> dict:
    """
    Read proxy configuration from SYS_NET plugin settings.
    Bypass proxy for free APIs (Pollinations/Airforce) to avoid timeouts over Tor.
    """
    if provider in ["pollinations", "airforce", "huggingface"]:
        return {}
        
    try:
        from app.config import ConfigManager
        cfg = ConfigManager()
        proxy_url = cfg.get_plugin_config("SYS_NET", "proxy_url", "").strip()
        if proxy_url:
            return {"http": proxy_url, "https": proxy_url}
    except Exception as e:
        log_debug(f"[Engine] Proxy config error: {e}")
    return {}

def ensure_english_prompt(prompt: str) -> str:
    """
    Translates prompt to English using googletrans (lightweight).
    Falls back to original prompt if translation fails.
    Required for providers that only accept English (Stability, OpenAI).
    """
    try:
        from googletrans import Translator
        t = Translator()
        detected = t.detect(prompt)
        if detected and detected.lang and detected.lang != 'en':
            result = t.translate(prompt, dest='en')
            translated = result.text
            log_debug(f"[Engine] Auto-translated prompt: '{prompt[:40]}' -> '{translated[:40]}'")
            return translated
    except ImportError:
        pass  # googletrans not installed, try Google translate via requests
    except Exception as e:
        log_debug(f"[Engine] Auto-translate error: {e}")

    # Fallback: use Google Translate unofficial API via requests (no key needed)
    try:
        import requests as _req
        enc = urllib.parse.quote(prompt)
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=en&dt=t&q={enc}"
        r = _req.get(url, timeout=5, proxies=get_proxies())
        if r.status_code == 200:
            data = r.json()
            translated = "".join([item[0] for item in data[0] if item[0]])
            if translated and translated.lower() != prompt.lower():
                log_debug(f"[Engine] Auto-translated (API): '{prompt[:40]}' -> '{translated[:40]}'")
                return translated
    except Exception as e2:
        log_debug(f"[Engine] Google Translate API fallback error: {e2}")

    return prompt  # Return original if all translation fails
