"""
MODULE: core/llm/vision/ollama_vision.py
PURPOSE: Vision adapter for Ollama models that support vision (llava, llava-llama3, etc.)

Ollama vision uses the standard OpenAI chat format with images encoded as base64
passed in the 'images' field of the extra_body OR as image_url content parts
(LiteLLM handles both via the openai-compatible Ollama endpoint).
"""

from .base import VisionAdapter, encode_image_b64


class OllamaVisionAdapter(VisionAdapter):

    def is_supported(self) -> bool:
        return True

    def build_messages(self, system_prompt: str, user_message: str, images: list[dict]) -> list[dict]:
        """
        Ollama: same format as OpenAI multipart. LiteLLM translates for Ollama's API.
        """
        content = [{"type": "text", "text": user_message}]

        for img in images:
            b64 = img.get("data_b64") or encode_image_b64(img.get("data", b""))
            mime = img.get("mime_type", "image/jpeg")
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:{mime};base64,{b64}"}
            })

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": content}
        ]
