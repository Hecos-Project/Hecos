"""
hecos/modules/executor/http_probe.py
Local URL extraction and safe loopback HTTP GET health + asset verification.
"""

from __future__ import annotations

import re
import time
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from .file_manager import logger

_LOCAL_URL_RE = re.compile(
    r"https?://(?:127\.0\.0\.1|localhost|0\.0\.0\.0):\d{2,5}(?:/[^\s\"'<>)\]]*)?",
    re.IGNORECASE,
)
_HTTP_PORT_HINT_RE = re.compile(
    r"(?:on|port|listening on)\s+(?:0\.0\.0\.0|127\.0\.0\.1|localhost)?\s*(?:port\s+)?(\d{4,5})",
    re.IGNORECASE,
)
_LOCAL_HTML_ASSET_RE = re.compile(
    r"""<(?:link\b[^>]*?\bhref|script\b[^>]*?\bsrc)=['"]([^'"]+)['"]""",
    re.IGNORECASE,
)


def extract_local_urls(text: str) -> List[str]:
    """Extract unique localhost / 127.0.0.1 HTTP URLs from process output."""
    if not text:
        return []
    found: List[str] = []
    seen = set()
    for match in _LOCAL_URL_RE.finditer(text):
        url = match.group(0).rstrip(".,;:")
        url = url.replace("://0.0.0.0:", "://127.0.0.1:")
        if url not in seen:
            seen.add(url)
            found.append(url)
    if not found:
        for m in _HTTP_PORT_HINT_RE.finditer(text):
            port = int(m.group(1))
            if 1024 <= port <= 65535:
                url = f"http://127.0.0.1:{port}"
                if url not in seen:
                    seen.add(url)
                    found.append(url)
    return found


def _is_loopback_http_url(url: str) -> bool:
    try:
        parsed = urlparse((url or "").strip())
        return parsed.scheme in {"http", "https"} and (parsed.hostname or "").lower() in {"127.0.0.1", "localhost"}
    except Exception:
        return False


def _probe_single_get(url: str, timeout: float) -> tuple[Optional[int], str, bytes, Optional[str]]:
    req = Request(url, headers={"User-Agent": "Hecos-Executor-Probe/1.0"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            status = int(getattr(resp, "status", 200) or 200)
            ctype = (resp.headers.get("Content-Type") or "").lower()
            body = resp.read(65536)
            return status, ctype, body, None
    except HTTPError as herr:
        body = b""
        try:
            body = herr.read(16384)
        except Exception:
            pass
        return (
            int(herr.code),
            (herr.headers.get("Content-Type") or "").lower() if herr.headers else "",
            body,
            f"HTTP {herr.code} {herr.reason}",
        )
    except URLError as uerr:
        return None, "", b"", str(uerr.reason or uerr)
    except Exception as exc:
        return None, "", b"", str(exc)


def probe_local_http_url(
    url: str,
    timeout: float = 2.0,
    *,
    check_assets: bool = True,
    retries: int = 3,
) -> Dict[str, Any]:
    """
    Perform a safe HTTP GET health probe against a localhost/127.0.0.1 app URL
    and verify local CSS/JS assets referenced by the returned HTML page.
    """
    clean_url = (url or "").strip()
    if not _is_loopback_http_url(clean_url):
        return {"ok": False, "url": clean_url, "error": "Only localhost / 127.0.0.1 HTTP URLs are allowed."}

    status: Optional[int] = None
    ctype = ""
    body = b""
    err_msg: Optional[str] = None
    attempts = max(1, min(int(retries), 5))
    for attempt in range(attempts):
        status, ctype, body, err_msg = _probe_single_get(clean_url, timeout=float(timeout))
        if status is not None:
            break
        if attempt + 1 < attempts:
            time.sleep(0.25)

    assets_checked = 0
    asset_errors: List[str] = []
    if check_assets and status is not None and 200 <= status < 400 and ("html" in ctype or b"<html" in body[:512].lower()):
        html_text = body.decode("utf-8", errors="replace")
        seen_assets = set()
        base_netloc = urlparse(clean_url).netloc
        for raw_ref in _LOCAL_HTML_ASSET_RE.findall(html_text):
            ref = raw_ref.strip()
            low = ref.lower()
            if not ref or low.startswith(("data:", "javascript:", "mailto:", "#")):
                continue
            resolved = urljoin(clean_url if clean_url.endswith("/") else clean_url + "/", ref)
            parsed_asset = urlparse(resolved)
            if parsed_asset.netloc != base_netloc:
                continue
            if resolved in seen_assets:
                continue
            seen_assets.add(resolved)
            if len(seen_assets) > 8:
                break
            assets_checked += 1
            a_status, _, _, a_err = _probe_single_get(resolved, timeout=min(float(timeout), 1.5))
            if a_status is None or a_status >= 400:
                code_txt = f"HTTP {a_status}" if a_status is not None else (a_err or "unreachable")
                asset_errors.append(f"{parsed_asset.path} -> {code_txt}")

    main_ok = status is not None and 200 <= status < 400
    overall_ok = main_ok and not asset_errors
    summary_parts = []
    if status is None:
        summary_parts.append(f"HTTP unreachable ({err_msg or 'connection error'})")
    else:
        summary_parts.append(f"HTTP {status} ({len(body)}B)")
    if assets_checked:
        ok_assets = assets_checked - len(asset_errors)
        summary_parts.append(f"assets={ok_assets}/{assets_checked}")
    if asset_errors:
        summary_parts.append("asset_errors=[" + ", ".join(asset_errors) + "]")
    summary = " | ".join(summary_parts)

    log_fn = logger.info if overall_ok else logger.warning
    log_fn(f"[RUNNER] http_probe url={clean_url} -> {summary}")
    return {
        "ok": overall_ok,
        "url": clean_url,
        "status_code": status,
        "content_type": ctype,
        "body_bytes": len(body),
        "assets_checked": assets_checked,
        "asset_errors": asset_errors,
        "error": err_msg if not main_ok else ("; ".join(asset_errors) if asset_errors else None),
        "summary": summary,
    }
