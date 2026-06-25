"""
image_gen — Provider Utilities (Autonomous)
Adapted from hecos/core/media/image_providers/utils.py
No hecos.core imports.
"""
import os
import uuid
import urllib.parse
import datetime

try:
    from hecos.core.logging import logger
except ImportError:
    class _Logger:
        def info(self, *a): print("[IMGPROVIDER]", *a)
        def error(self, *a): print("[IMGPROVIDER ERROR]", *a)
        def debug(self, *a): pass
    logger = _Logger()

try:
    from hecos.core.constants import IMAGES_DIR, LOGS_DIR
except ImportError:
    # Fallback: use standard Hecos paths relative to cwd
    _base = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "hecos")
    IMAGES_DIR = os.path.join(_base, "media", "images")
    LOGS_DIR   = os.path.join(_base, "logs")


def log_debug(msg: str):
    log_file = os.path.join(LOGS_DIR, "image_gen_debug.txt")
    now = datetime.datetime.now().strftime("%H:%M:%S")
    try:
        os.makedirs(LOGS_DIR, exist_ok=True)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{now}] {msg}\n")
    except Exception:
        pass


def save_image_bytes(data: bytes, ext: str = "jpg", prompt: str = "", params: dict = None) -> str:
    import re
    os.makedirs(IMAGES_DIR, exist_ok=True)

    now = datetime.datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    safe_prompt = re.sub(r'[^a-zA-Z0-9]', '_', prompt[:50]).strip('_')
    if not safe_prompt:
        safe_prompt = "generation"

    filename = f"gen_{timestamp}_{safe_prompt}.{ext}"
    path = os.path.join(IMAGES_DIR, filename)

    if os.path.exists(path):
        filename = f"gen_{timestamp}_{uuid.uuid4().hex[:4]}_{safe_prompt}.{ext}"
        path = os.path.join(IMAGES_DIR, filename)

    with open(path, "wb") as f:
        f.write(data)

    # Sidecar metadata
    try:
        meta_path = path.rsplit('.', 1)[0] + ".txt"
        with open(meta_path, "w", encoding="utf-8") as f:
            f.write("HECOS IMAGE METADATA\n=====================\n")
            f.write(f"Date: {now.strftime('%Y-%m-%d %H:%M:%S')}\n")
            if params:
                for k, v in params.items():
                    f.write(f"{k.capitalize()}: {v}\n")
            f.write(f"Prompt: {prompt}\n")
    except Exception as e:
        logger.error(f"[ImageEngine] Failed to save metadata: {e}")

    return filename


def get_proxies(provider: str = "") -> dict:
    """Read proxy config from SYS_NET plugin settings. Bypass for free providers."""
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
    """Translates prompt to English. Falls back to original on failure."""
    try:
        from googletrans import Translator
        t = Translator()
        detected = t.detect(prompt)
        if detected and detected.lang and detected.lang != 'en':
            result = t.translate(prompt, dest='en')
            log_debug(f"[Engine] Auto-translated: '{prompt[:40]}' -> '{result.text[:40]}'")
            return result.text
    except ImportError:
        pass
    except Exception as e:
        log_debug(f"[Engine] Auto-translate error: {e}")

    # Fallback: Google Translate unofficial API
    try:
        import requests as _req
        enc = urllib.parse.quote(prompt)
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=en&dt=t&q={enc}"
        r = _req.get(url, timeout=5, proxies=get_proxies())
        if r.status_code == 200:
            data = r.json()
            translated = "".join([item[0] for item in data[0] if item[0]])
            if translated and translated.lower() != prompt.lower():
                log_debug(f"[Engine] Translated (API): '{prompt[:40]}' -> '{translated[:40]}'")
                return translated
    except Exception as e2:
        log_debug(f"[Engine] Google Translate fallback error: {e2}")

    return prompt
