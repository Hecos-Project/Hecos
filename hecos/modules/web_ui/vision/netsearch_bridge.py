"""
hecos/modules/web_ui/vision/netsearch_bridge.py
Connects Hecos Net Search sessions with the Unified Multimodal Perception pipeline.
Extracts media result thumbnails from search sessions, fetches them resiliently,
and prepares them for AI visual verification.
"""
import logging
from typing import Optional, List

from .config import load_vision_config
from .processor import fetch_image_from_url, bytes_to_b64_dict

logger = logging.getLogger("hecos.web_ui.vision.netsearch_bridge")


def extract_search_session_images(session_id: str, config: Optional[dict] = None) -> List[dict]:
    """
    Loads a search session from SQLite, picks the top media thumbnails,
    downloads them and returns a list of vision dicts [{"data_b64": ..., "mime_type": ..., "name": ...}].
    """
    if not session_id:
        return []

    cfg = config or load_vision_config()
    if not cfg.get("enabled", True):
        return []

    ns_cfg = cfg.get("net_search", {})
    if not ns_cfg.get("verify_results", True):
        logger.debug("[NetSearchVisionBridge] Result verification disabled in config.")
        return []

    max_thumbs = ns_cfg.get("max_thumbnails", 4)
    timeout = cfg.get("timeout_seconds", 5)
    max_px = cfg.get("max_resolution_px", 512)
    quality = cfg.get("jpeg_quality", 80)

    try:
        from hecos.modules.net_search.search.sessions import get_session_store
        session = get_session_store().get_session(session_id)
        if not session or not session.results:
            logger.debug(f"[NetSearchVisionBridge] Session '{session_id}' has no results.")
            return []
    except Exception as e:
        logger.warning(f"[NetSearchVisionBridge] Could not load session '{session_id}': {e}")
        return []

    # Filter candidate URLs
    candidates = []
    seen = set()

    # Pass 1: Media categories (images, videos)
    for r in session.results:
        if len(candidates) >= max_thumbs:
            break
        url = getattr(r, "thumbnail_url", None) or getattr(r, "media_url", None)
        if url and url not in seen and url.startswith("http"):
            seen.add(url)
            candidates.append((url, r.title or "search_result"))

    # Pass 2: Any result with thumbnail
    for r in session.results:
        if len(candidates) >= max_thumbs:
            break
        url = getattr(r, "thumbnail_url", None)
        if url and url not in seen and url.startswith("http"):
            seen.add(url)
            candidates.append((url, r.title or "search_result"))

    logger.info(f"[NetSearchVisionBridge] Found {len(candidates)} thumbnail candidate(s) for session '{session_id}'")

    images_out = []
    for idx, (thumb_url, title) in enumerate(candidates, start=1):
        raw = fetch_image_from_url(thumb_url, timeout=timeout, use_proxy=True)
        if raw:
            safe_name = f"search_thumb_{idx}.jpg"
            img_dict = bytes_to_b64_dict(raw, name=safe_name, max_px=max_px, quality=quality)
            if img_dict:
                img_dict["title"] = title
                images_out.append(img_dict)

    logger.info(f"[NetSearchVisionBridge] Downloaded {len(images_out)}/{len(candidates)} thumbnails for verification.")
    return images_out

