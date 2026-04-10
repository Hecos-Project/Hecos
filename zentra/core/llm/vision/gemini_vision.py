"""
MODULE: core/llm/vision/gemini_vision.py
PURPOSE: Vision adapter for Google Gemini models (gemini-1.5-pro, gemini-2.0-flash, etc.)

Gemini uses a single "user" message with inline_data parts:
  {
    "role": "user",
    "content": [
      {"type": "text", "text": "..."},
      {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}}
    ]
  }

LiteLLM normalises this automatically for Gemini when using OpenAI-style content parts.
"""

from .base import VisionAdapter, encode_image_b64


class GeminiVisionAdapter(VisionAdapter):

    def is_supported(self) -> bool:
        return True

    def build_messages(self, system_prompt: str, user_message: str, images: list[dict]) -> list[dict]:
        """
        Gemini: system prompt + user text + images all go in a single user message
        using OpenAI-compatible multipart content format (LiteLLM handles translation).
        """
        content = []

        # 1. We now properly support the system role
        system_msg = {"role": "system", "content": system_prompt}

        # 2. User text and image parts
        content.append({
            "type": "text",
            "text": user_message
        })

        for img in images:
            b64 = img.get("data_b64") or encode_image_b64(img.get("data", b""))
            mime = img.get("mime_type", "image/jpeg")
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{mime};base64,{b64}"
                }
            })

        return [system_msg, {"role": "user", "content": content}]
