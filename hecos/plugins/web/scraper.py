import re

try:
    from hecos.core.logging import logger
except ImportError:
    class DummyLogger:
        def error(self, *args, **kwargs): print("[WEB_ERR]", *args)
    logger = DummyLogger()

try:
    from app.config import ConfigManager
except ImportError:
    class DummyConfig:
        def get_plugin_config(self, tag, key, default): return default
    def FakeConfigManager(): return DummyConfig()
    ConfigManager = FakeConfigManager

def ensure_https(url: str) -> str:
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url

def extract_text(html: str, max_chars: int = 4000) -> str:
    """Extract readable text from HTML. Tries trafilatura → BeautifulSoup → regex."""
    try:
        import trafilatura
        result = trafilatura.extract(html, include_comments=False, include_tables=False)
        if result and len(result.strip()) > 100:
            return result.strip()[:max_chars]
    except ImportError:
        pass

    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        lines = [l for l in text.splitlines() if len(l.strip()) > 20]
        return "\n".join(lines)[:max_chars]
    except ImportError:
        pass

    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)
    return text.strip()[:max_chars]

def http_get(url: str, tag: str = "WEB") -> str | None:
    """Fetches raw HTML from a URL using httpx → requests → urllib fallback."""
    cfg = ConfigManager()
    timeout = cfg.get_plugin_config(tag, "fetch_timeout", 10)
    headers = {"User-Agent": "Mozilla/5.0 (compatible; Hecos/1.0; +https://hecos.ai)"}
    try:
        import httpx
        r = httpx.get(url, headers=headers, timeout=timeout, follow_redirects=True)
        r.raise_for_status()
        return r.text
    except ImportError:
        pass
    try:
        import requests
        r = requests.get(url, headers=headers, timeout=timeout)
        r.raise_for_status()
        return r.text
    except ImportError:
        pass
    try:
        import urllib.request as ureq
        req = ureq.Request(url, headers=headers)
        with ureq.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        logger.error(f"[{tag}] HTTP fetch failed for {url}: {e}")
        return None
