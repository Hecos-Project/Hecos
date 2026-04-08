"""
MODULE: core/llm/vision/openai_vision.py
PURPOSE: Vision adapter for OpenAI models that support vision (gpt-4o, gpt-4-turbo, etc.)

OpenAI uses separate system + user messages.
User message content is a list of parts (text + image_url).
"""

from .base import VisionAdapter, encode_image_b64


class OpenAIVisionAdapter(VisionAdapter):

    def is_supported(self) -> bool:
        return True

    def build_messages(self, system_prompt: str, user_message: str, images: list[dict]) -> list[dict]:
        """
        OpenAI: system message + user message with multipart content.
        """
        content = [{"type": "text", "text": user_message}]

        for img in images:
            b64 = img.get("data_b64") or encode_image_b64(img.get("data", b""))
            mime = img.get("mime_type", "image/jpeg")
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{mime};base64,{b64}",
                    "detail": "auto"
                }
            })

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": content}
        ]
