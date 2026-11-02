"""
hecos/modules/web_ui/vision/router.py
Unified Multimodal Perception Router.
Routes images between native vision models and the Vision Bridge (for text-only models).
"""
import os
import re
import logging
from typing import Optional, List, Tuple

from .config import load_vision_config
from .processor import optimize_image_bytes, bytes_to_b64_dict
from .inspector import inspect_image

logger = logging.getLogger("hecos.web_ui.vision.router")


class VisionRouter:
    """
    Main dispatch and perception coordinator.
    Ensures that every model (native multimodal or text-only) can perceive images.
    """

    @classmethod
    def process_incoming_turn(
        cls,
        user_message: str,
        images: Optional[List[dict]],
        model_name: str,
        backend_type: str,
        emit_callback=None
    ) -> Tuple[str, Optional[List[dict]]]:
        """
        Coordinates visual perception before the LLM call.

        Args:
            user_message:  Original user message.
            images:        List of image dicts [{"data_b64": ..., "mime_type": ..., "name": ...}]
            model_name:    Active LLM model name.
            backend_type:  Backend type ('ollama', 'cloud', 'kobold', 'llama_cpp').
            emit_callback: Optional callback for agent/chat traces.

        Returns:
            Tuple of (possibly_enriched_user_message, possibly_filtered_images).
        """
        if not images:
            return user_message, None

        cfg = load_vision_config()
        if not cfg.get("enabled", True):
            logger.info("[VisionRouter] Multimodal Perception disabled in vision.yaml.")
            return user_message, None

        # Check if the active model natively supports multimodal vision
        from hecos.core.llm.vision.factory import get_vision_adapter
        adapter = get_vision_adapter(model_name, backend_type)

        # ── TRACK 1: Native Multimodal Model (Gemini, GPT-4o, LLaVA, etc.) ────
        if adapter is not None:
            logger.info(
                f"[VisionRouter] Native multimodal adapter available ({adapter.__class__.__name__}) "
                f"for model '{model_name}'. Passing {len(images)} image(s) directly."
            )
            if emit_callback:
                try:
                    emit_callback(f"Vision: streaming {len(images)} image(s) to native multimodal model...", level="info")
                except Exception:
                    pass

            # Optimize images according to config limits
            optimized_images = cls._optimize_images_list(images, cfg)
            return user_message, optimized_images

        # ── TRACK 2: Text-Only Model -> Activate Vision Bridge / Sidecar ───────
        bridge_cfg = cfg.get("bridge", {})
        if not bridge_cfg.get("enabled", True):
            logger.info(
                f"[VisionRouter] Model '{model_name}' is text-only and Vision Bridge is disabled. Images dropped."
            )
            return user_message, None

        logger.info(
            f"[VisionRouter] Model '{model_name}' is text-only -> Activating Vision Bridge for {len(images)} image(s)..."
        )
        if emit_callback:
            try:
                emit_callback(
                    f"Vision Bridge: analyzing {len(images)} image(s) for local model...",
                    level="info"
                )
            except Exception:
                pass

        descriptions = []
        for idx, img in enumerate(images, start=1):
            fname = img.get("name", f"image_{idx}.jpg")
            title = img.get("title")
            title_header = f" — Source: {title}" if title else ""
            logger.info(f"[VisionRouter] Bridge inspecting [{idx}/{len(images)}]: '{fname}'{title_header}...")
            desc = inspect_image(img, config=cfg)
            if desc:
                descriptions.append(f"### [Image {idx}: {fname}{title_header}]\n{desc}")
                logger.info(f"[VisionRouter] Inspection complete for '{fname}' ({len(desc)} chars)")
            else:
                logger.warning(f"[VisionRouter] Inspection failed for '{fname}'")

        if descriptions:
            vision_block = (
                "\n\n---\n"
                "**[MULTIMODAL PERCEPTION SYSTEM — VERIFIED IMAGE ANALYSIS]**\n"
                "The following visual elements were extracted directly from the user's images by the vision system. "
                "Use this verified visual analysis to accurately understand what is in the picture:\n\n"
                + "\n\n".join(descriptions) +
                "\n---\n"
            )
            enriched_message = user_message + vision_block
            if emit_callback:
                try:
                    emit_callback(
                        f"Vision Bridge: visual context successfully injected for {len(descriptions)} image(s).",
                        level="success"
                    )
                except Exception:
                    pass
            # Return enriched message and None for images (since local text model cannot receive raw b64)
            return enriched_message, None

        # If all inspections failed (e.g. content_filter / NSFW block or timeout)
        if emit_callback:
            try:
                emit_callback(
                    "Vision Bridge: inspection failed or blocked by safety filter.",
                    level="warning"
                )
            except Exception:
                pass

        fail_notice = (
            "\n\n---\n"
            "**[MULTIMODAL PERCEPTION NOTICE]**\n"
            "The user attached an image, but the vision inspector could NOT analyze it (the image was blocked by content/safety filters or the vision service was unavailable). "
            "Clearly inform the user that you cannot see the image because the vision inspection failed or was blocked by content safety filters. "
            "Do NOT invent, guess, or hallucinate the visual content of the image.\n"
            "---\n"
        )
        return user_message + fail_notice, None

    @classmethod
    def _optimize_images_list(cls, images: List[dict], cfg: dict) -> List[dict]:
        """Resizes images to config limits if raw bytes are available or decodes b64 to resize."""
        import base64
        max_px = cfg.get("max_resolution_px", 512)
        quality = cfg.get("jpeg_quality", 80)

        optimized = []
        for img in images:
            b64_data = img.get("data_b64")
            raw_bytes = img.get("data")
            if not raw_bytes and b64_data:
                try:
                    raw_bytes = base64.b64decode(b64_data)
                except Exception:
                    pass

            if raw_bytes:
                opt_dict = bytes_to_b64_dict(
                    raw_bytes,
                    name=img.get("name", "image.jpg"),
                    max_px=max_px,
                    quality=quality
                )
                if opt_dict:
                    optimized.append(opt_dict)
                    continue

            # Fallback to original dict if re-encoding fails
            optimized.append(img)

        return optimized
