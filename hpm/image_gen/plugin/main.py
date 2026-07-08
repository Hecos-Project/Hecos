"""
Plugin: Image Generation â€” Entry Point
Thin wrapper: registers the tool, delegates all logic to sub-modules.
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
    def __init__(self):
        self.tag    = "IMAGE_GEN"
        self.desc   = "Generates images from text descriptions using AI image models."
        self.status = "ONLINE"
        self.slash_commands = [
            {
                "id": "img",
                "aliases": ["/img", "/image", "/photo", "/foto"],
                "description": "Genera un'immagine AI da una descrizione testuale",
                "usage": "/img <descrizione>",
                "example": "/img foto fotorealistica di un gatto su Marte",
                "icon": "ðŸ–¼ï¸",
                "method": "generate_image",
                "args_schema": {"prompt": "str"},
                "requires_args": True,
            }
        ]

    def generate_image(self, prompt: str) -> str:
        """
        Generates an image from a text description.

        IMPORTANT: You MUST include the exact [[IMG:filename.ext]] tag
        returned by this function in your final response so the user can see the image!
        """
        logger.info(f"[IMAGE_GEN] generate_image called. Prompt: {prompt[:60]}...")
        return run_generation(prompt)


# â”€â”€ Module exports â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
tools = ImageGenTools()

def info():
    return {"tag": tools.tag, "desc": tools.desc}

def status():
    return tools.status

