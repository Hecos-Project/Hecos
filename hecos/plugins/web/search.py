import webbrowser
import urllib.parse
import re

try:
    from hecos.core.logging import logger
    from hecos.core.i18n import translator
except ImportError:
    class DummyLogger:
        def debug(self, *args, **kwargs): print("[WEB_DEBUG]", *args)
        def info(self, *args, **kwargs): print("[WEB_INFO]", *args)
    logger = DummyLogger()
    class DummyTranslator:
        def t(self, key, **kwargs): return key
    translator = DummyTranslator()

try:
    from app.config import ConfigManager
except ImportError:
    class DummyConfig:
        def get_plugin_config(self, tag, key, default): return default
    def FakeConfigManager(): return DummyConfig()
    ConfigManager = FakeConfigManager

# Relative imports from our new modules
from .scraper import ensure_https, extract_text, http_get

def _get_search_url(query: str, tag: str) -> str:
    cfg = ConfigManager()
    engine = cfg.get_plugin_config(tag, "search_engine", "google")
    q = urllib.parse.quote(query)
    if engine == "duckduckgo":
        return f"https://duckduckgo.com/?q={q}"
    elif engine == "bing":
        return f"https://www.bing.com/search?q={q}"
    return f"https://www.google.com/search?q={q}"

def _open_target_url(url: str, tag: str):
    cfg = ConfigManager()
    use_https = cfg.get_plugin_config(tag, "use_https", True)
    open_new = cfg.get_plugin_config(tag, "open_in_new_tab", False)
    if use_https and not url.startswith(("http://", "https://")):
        url = "https://" + url
    if open_new:
        webbrowser.open_new_tab(url)
    else:
        webbrowser.open(url)

def open_url_tool(url: str, tag: str) -> str:
    addr = url.strip()
    logger.debug(f"PLUGIN_{tag}", f"Opening site: {addr}")
    try:
        _open_target_url(addr, tag)
        return translator.t("plugin_web_open_success", url=addr)
    except Exception as e:
        logger.error(f"PLUGIN_{tag}: Error: {e}")
        return translator.t("plugin_web_error_network", error=str(e))

def search_web_tool(query: str, tag: str) -> str:
    ricerca = query.strip()
    logger.debug(f"PLUGIN_{tag}", f"Searching: {ricerca}")
    try:
        url_ricerca = _get_search_url(ricerca, tag)
        _open_target_url(url_ricerca, tag)
        return translator.t("plugin_web_search_success", query=ricerca)
    except Exception as e:
        logger.error(f"PLUGIN_{tag}: Error: {e}")
        return translator.t("plugin_web_error_network", error=str(e))

def fetch_page_content_tool(url: str, tag: str, max_chars_override: int = None) -> str:
    url = ensure_https(url)
    logger.info(f"[{tag}] fetch_page_content: {url}")
    html = http_get(url, tag)
    if html is None:
        return f"[{tag}] Failed to fetch page: {url}. Check the URL and network connection."
    
    cfg = ConfigManager()
    max_chars = cfg.get_plugin_config(tag, "max_content_chars", 4000)
    
    try:
        if max_chars_override is not None:
            max_chars = int(max_chars_override)
        else:
            max_chars = int(max_chars)
    except (ValueError, TypeError):
        max_chars = 4000

    text = extract_text(html, max_chars)
    if not text or len(text.strip()) < 50:
        return f"[{tag}] Page fetched but no readable content found at: {url}"
    return f"📄 Content from {url}:\n\n{text}"

def search_and_read_tool(query: str, tag: str, max_results: int = 3) -> str:
    try:
        max_res_int = int(max_results)
    except (ValueError, TypeError):
        max_res_int = 3

    BLOCKED_DOMAINS = [
        "duckduckgo.com", "doubleclick.net", "adservice.google.com", "ads.",
        "youtube.com", "youtu.be",
        "google.com", "google.it", "google.co.",
        "facebook.com", "instagram.com",
        "twitter.com", "x.com",
        "tiktok.com",
        "whatsapp.com",
        "linkedin.com/feed",
    ]

    q = query.strip()
    logger.info(f"[{tag}] search_and_read: {q!r}")

    search_url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(q)}"
    html = http_get(search_url, tag)
    if html is None:
        return f"[{tag}] Could not reach DuckDuckGo. Check your internet connection."

    raw_links = re.findall(r'uddg=(https?(?:%3A|:)[^&"\'\\s]+)', html, re.IGNORECASE)
    redirect_links = re.findall(r'href="//duckduckgo\.com/l/\?uddg=(https?(?:%3A|:)[^&"]+)"', html, re.IGNORECASE)
    raw_links.extend(redirect_links)

    seen_urls: dict[str, None] = {}
    for raw in raw_links:
        try:
            decoded = urllib.parse.unquote(raw).strip()
            if any(bad in decoded for bad in BLOCKED_DOMAINS):
                continue
            if not decoded.startswith(("http://", "https://")):
                continue
            seen_urls[decoded] = None
        except Exception:
            continue

    limit = max(1, min(max_res_int, 5))
    urls = list(seen_urls.keys())[:limit]

    if not urls:
        return f"[{tag}] No usable results found for: '{q}'. Try a different query."

    cfg = ConfigManager()
    try:
        max_chars = int(cfg.get_plugin_config(tag, "max_content_chars", 4000))
    except (ValueError, TypeError):
        max_chars = 4000

    per_page = max(800, max_chars // len(urls))

    results = [f"🔍 Search results for: \"{q}\"\n"]
    good_results = 0
    for i, url in enumerate(urls, 1):
        logger.info(f"[{tag}] Reading result {i}/{len(urls)}: {url}")
        page_html = http_get(url, tag)
        if page_html is None:
            results.append(f"[{i}] ⚠️  Could not read: {url}")
            continue
        text = extract_text(page_html, per_page)
        if text and len(text.strip()) > 50:
            results.append(f"[{i}] 📄 {url}\n{text}\n")
            good_results += 1
        else:
            results.append(f"[{i}] ⚠️  No readable content at: {url}")

    if good_results == 0:
        return (
            f"[{tag}] Unable to read any results for '{q}'. "
            f"This is likely a temporary network issue — please retry in a moment. "
            f"Checked {len(urls)} URL(s)."
        )

    return "\n---\n".join(results)
