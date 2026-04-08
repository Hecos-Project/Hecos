import os
import uuid
import urllib.parse
import datetime

try:
    from core.logging import logger
except ImportError:
    class _Logger:
        def info(self, *a): print("[IMGPROVIDER]", *a)
        def error(self, *a): print("[IMGPROVIDER ERROR]", *a)
        def debug(self, *a): pass
    logger = _Logger()

OUTPUT_DIR = "data/images"

def log_debug(msg: str):
    log_file = "logs/image_gen_debug.txt"
    now = datetime.datetime.now().strftime("%H:%M:%S")
    try:
        os.makedirs("logs", exist_ok=True)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{now}] {msg}\n")
    except Exception:
        pass

def save_image_bytes(data: bytes, ext: str = "jpg") -> str:
    """Save raw image bytes to data/images/ and return filename."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filename = f"gen_{uuid.uuid4().hex[:8]}.{ext}"
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "wb") as f:
        f.write(data)
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
