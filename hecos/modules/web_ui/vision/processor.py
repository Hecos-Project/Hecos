"""
hecos/modules/web_ui/vision/processor.py
Image processing, Pillow optimization, resizing, Base64 conversion,
and resilient thumbnail fetching.
"""
import io
import base64
import logging
import urllib.request
import urllib.error
import urllib.parse
from typing import Optional, Tuple

logger = logging.getLogger("hecos.web_ui.vision.processor")

try:
    from PIL import Image as _PILImage
    _PIL_OK = True
except ImportError:
    _PIL_OK = False
    logger.warning("[VisionProcessor] Pillow not available — images will not be resized.")


def optimize_image_bytes(
    raw_bytes: bytes,
    max_px: int = 512,
    quality: int = 80,
    target_mime: str = "image/jpeg"
) -> Tuple[bytes, str]:
    """
    Resizes image proportionally if its longest dimension exceeds max_px.
    Converts RGBA/palette to RGB and compresses as JPEG.
    Returns (optimized_bytes, mime_type).
    """
    if not raw_bytes or not _PIL_OK or max_px <= 0:
        return raw_bytes, target_mime

    try:
        img = _PILImage.open(io.BytesIO(raw_bytes))
        w, h = img.size

        # Only resize if larger than max_px
        if max(w, h) > max_px:
            ratio = max_px / max(w, h)
            new_w = max(1, int(w * ratio))
            new_h = max(1, int(h * ratio))
            img = img.resize((new_w, new_h), _PILImage.LANCZOS)
            logger.debug(f"[VisionProcessor] Resized {w}x{h} -> {new_w}x{new_h}")

        # Convert transparency modes to RGB for clean JPEG compression
        if img.mode in ("RGBA", "P", "LA", "CMYK"):
            img = img.convert("RGB")

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        return buf.getvalue(), "image/jpeg"

    except Exception as e:
        logger.debug(f"[VisionProcessor] Pillow optimization skipped: {e}")
        return raw_bytes, target_mime


def bytes_to_b64_dict(
    raw_bytes: bytes,
    name: str = "image.jpg",
    max_px: int = 512,
    quality: int = 80
) -> Optional[dict]:
    """
    Takes raw image bytes, optimizes them, and returns a standard vision dict:
    {"data_b64": "...", "mime_type": "image/jpeg", "name": "..."}
    """
    if not raw_bytes:
        return None

    try:
        opt_bytes, mime = optimize_image_bytes(raw_bytes, max_px=max_px, quality=quality)
        b64 = base64.b64encode(opt_bytes).decode("utf-8")
        return {
            "data_b64": b64,
            "mime_type": mime,
            "name": name
        }
    except Exception as e:
        logger.error(f"[VisionProcessor] Error converting bytes to b64: {e}")
        return None


def fetch_image_from_url(url: str, timeout: int = 5, use_proxy: bool = True) -> Optional[bytes]:
    """
    Downloads an image from a URL with browser headers and server proxy fallback.
    """
    if not url or not isinstance(url, str):
        return None

    # Try via server-side media proxy first if enabled
    if use_proxy and not url.startswith("http://127.0.0.1") and not url.startswith("http://localhost"):
        try:
            proxy_url = f"http://127.0.0.1:5000/api/hsearch/media_proxy?url={urllib.parse.quote(url, safe='')}"
            req = urllib.request.Request(proxy_url, headers={"User-Agent": "HecosVision/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = resp.read()
                if len(data) >= 512:
                    return data
        except Exception:
            pass  # Fall back to direct fetch below

    # Direct fetch
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "image/*,*/*;q=0.8"
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
            if len(data) >= 512:
                return data
    except Exception as e:
        logger.debug(f"[VisionProcessor] Direct download failed for {url[:70]}: {e}")

    return None

