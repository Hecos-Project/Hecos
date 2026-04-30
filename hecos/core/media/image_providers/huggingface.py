import os
from hecos.core.media.image_providers.utils import log_debug, save_image_bytes, get_proxies, ensure_english_prompt

class HuggingFaceProvider:
    NAME = "huggingface"

    @staticmethod
    def get_models() -> list:
        # Some highly popular and proven image generation models on HF Inference API
        return [
            "black-forest-labs/FLUX.1-schnell",
            "stabilityai/stable-diffusion-xl-base-1.0",
            "runwayml/stable-diffusion-v1-5",
            "prompthero/openjourney"
        ]

    @staticmethod
    def generate(prompt: str, width: int, height: int, model: str, api_key: str = "", 
                 negative_prompt: str = "", guidance_scale: float = 7.5, 
                 num_inference_steps: int = 30, seed: int = -1,
                 sampler: str = "", scheduler: str = "") -> str:
        """Generate image via Hugging Face Inference API."""
        if not api_key:
            api_key = os.environ.get("HUGGINGFACE_API_KEY", "").strip()
        if not api_key:
            raise Exception("Hugging Face API key not set. Add HUGGINGFACE_API_KEY to .env")

        eng_prompt = ensure_english_prompt(prompt)
        log_debug(f"[HuggingFace] model={model} prompt={eng_prompt[:50]}")

        import requests

        url = f"https://router.huggingface.co/hf-inference/models/{model}"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # We pass width/height conceptually if the model supports it in parameters,
        # otherwise basic string payload is used. Standard payload format:
        payload = {
            "inputs": eng_prompt,
            "parameters": {
                "width": width,
                "height": height,
                "negative_prompt": negative_prompt,
                "guidance_scale": guidance_scale,
                "num_inference_steps": num_inference_steps,
            }
        }
        # Optional params — add only when explicitly set
        params = payload["parameters"]
        if seed is not None and seed != -1:
            params["seed"] = seed
            
        # Flux models typically reject classical schedulers in Diffusers API
        if "flux" not in model.lower() and scheduler and scheduler.lower() not in ("", "none"):
            params["scheduler"] = scheduler

        prox = get_proxies(provider="huggingface")
        r = requests.post(url, headers=headers, json=payload, timeout=90, proxies=prox)
        
        # Automatic fallback for parameters rejected by specific pipelines (e.g. Flux, custom moes)
        if r.status_code == 400:
            err_text = r.text
            did_retry = False
            if "unexpected keyword argument 'scheduler'" in err_text and "scheduler" in params:
                params.pop("scheduler", None)
                did_retry = True
            elif "unexpected keyword argument 'guidance_scale'" in err_text and "guidance_scale" in params:
                params.pop("guidance_scale", None)
                did_retry = True
            
            if did_retry:
                log_debug(f"[HuggingFace] Retrying without incompatible parameter...")
                r = requests.post(url, headers=headers, json=payload, timeout=90, proxies=prox)

        log_debug(f"[HuggingFace] HTTP {r.status_code}, len={len(r.content)}")

        if r.status_code != 200:
            try:
                err_detail = r.json()
                if "error" in err_detail and "estimated_time" in err_detail:
                    # Model is loading into HF memory, common cold-start scenario
                    raise Exception(f"Model is loading on Hugging Face (estimated {err_detail['estimated_time']}s). Try again shortly.")
                raise Exception(f"HuggingFace HTTP {r.status_code}: {err_detail}")
            except ValueError:
                raise Exception(f"HuggingFace HTTP {r.status_code}: {r.text[:200]}")

        # The inference API directly returns the bytes of the image (JPEG/PNG)
        if r.content.startswith(b"<!DOCTYPE") or r.content.startswith(b"<html"):
            raise Exception("HuggingFace returned HTML instead of image")

        return save_image_bytes(r.content, "jpg", prompt=prompt, params={
            "provider": "huggingface",
            "model": model,
            "guidance_scale": guidance_scale,
            "inference_steps": num_inference_steps
        })
