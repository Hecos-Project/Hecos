"""
Plugin: Image Generation — Entry Point
Thin wrapper: registers the tool, delegates all logic to sub-modules.

Sub-module architecture:
  dimensions.py   — Aspect ratio → (width, height) resolver
  prompt_engine.py — Flux refinement, style injection, auto-enrich
  presets.py      — Built-in + user preset CRUD
  generator.py    — Core retry/key-rotation loop → provider engine
"""

try:
    from hecos.core.logging import logger
except ImportError:
    class _DummyLogger:
        def error(self, *a): print("[IMAGE_GEN ERR]", *a)
        def info(self, *a):  print("[IMAGE_GEN]", *a)
    logger = _DummyLogger()

from .generator import run_generation


class ImageGenTools:
    """
    Plugin: Image Generation
    Generates images from text prompts using external AI services.
    Supports: Pollinations (free), Gemini Imagen, OpenAI DALL-E,
              Stability AI, HuggingFace Inference API.
    """

    def __init__(self):
        self.tag    = "IMAGE_GEN"
        self.desc   = "Generates images from text descriptions using AI image models."
        self.status = "ONLINE"

    def generate_image(self, prompt: str) -> str:
        """
        Generates an image from a text description.
        Uses the provider/model/params configured in the Image Gen panel.

        IMPORTANT: You MUST include the exact [[IMG:filename.ext]] tag
        returned by this function in your final response so the user can see the image!

        :param prompt: Detailed description of the image to generate.
        """
        logger.info(f"[IMAGE_GEN] generate_image called. Prompt: {prompt[:60]}...")
        return run_generation(prompt)


# ── Module exports ─────────────────────────────────────────────────────────────
tools = ImageGenTools()


def info():
    return {"tag": tools.tag, "desc": tools.desc}


def status():
    return tools.status
