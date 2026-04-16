"""
Plugin: Image Generation
Delegates image generation to core/media/image_providers.py (multi-provider engine).
"""
try:
    from zentra.core.logging import logger
    from zentra.core.media_config import get_media_config
    from zentra.core.media.image_providers import generate_image, get_models_for_provider
except ImportError as _e:
    class _DummyLogger:
        def error(self, *a): print("[IMAGE_GEN ERR]", *a)
        def info(self, *a): print("[IMAGE_GEN]", *a)
    logger = _DummyLogger()
    def get_media_config(): return {"image_gen": {}}
    def generate_image(prompt, provider, model, width, height, api_key): raise Exception("Core imports failed")
    def get_models_for_provider(p): return []


class ImageGenTools:
    """
    Plugin: Image Generation
    Generates images from text prompts using external AI services.
    Supports: Pollinations (free), Gemini Imagen, OpenAI DALL-E, Stability.ai
    """

    def __init__(self):
        self.tag = "IMAGE_GEN"
        self.desc = "Generates images from text descriptions using AI image models."
        self.status = "ONLINE"

    def generate_image(self, prompt: str) -> str:
        """
        Generates an image from a text description. Uses the configured provider.
        IMPORTANT: You MUST include the exact [[IMG:filename.ext]] tag returned by this function in your final response to the user so they can see the image!
        
        :param prompt: Detailed description of the image to generate.
        """
        import os
        try:
            cfg = get_media_config().get("image_gen", {})
            provider = cfg.get("provider", "pollinations")
            model    = cfg.get("model", "flux")
            width    = int(cfg.get("width", 1024))
            height   = int(cfg.get("height", 1024))
            
            # 1) Try pinned key from config first if it exists
            pinned_key = cfg.get("api_key", "").strip()
            
            neg_prompt = cfg.get("negative_prompt", "")
            guidance   = float(cfg.get("guidance_scale", 7.5))
            steps      = int(cfg.get("num_inference_steps", 30))
            enrich     = cfg.get("auto_enrich", True)
            # New fields: enrich_keywords and style
            enrich_keywords = cfg.get("enrich_keywords", "")
            style = cfg.get("style", "none")

            max_attempts = 5
            attempt = 0
            last_error = None

            while attempt < max_attempts:
                attempt += 1
                api_key = pinned_key
                
                # 2) Fallback to KeyManager if no pinned key or pinned key failed
                if not api_key:
                    try:
                        from zentra.core.keys.key_manager import get_key_manager
                        manager = get_key_manager()
                        api_key = manager.get_key(provider)
                        logger.info(f"[IMAGE_GEN] KeyManager returned: {'YES' if api_key else 'NONE'} for {provider}")
                    except ImportError:
                        logger.error("[IMAGE_GEN] Could not import KeyManager")

                if not api_key and provider in ["gemini", "gemini_native", "openai", "stability", "huggingface"]:
                    # Final fallback to raw os.environ if KeyManager is empty
                    env_map = {
                        "gemini": "GEMINI_API_KEY",
                        "openai": "OPENAI_API_KEY",
                        "stability": "STABILITY_API_KEY",
                        "huggingface": "HUGGINGFACE_API_KEY",
                    }
                    var_name = env_map.get(provider, "")
                    api_key = os.environ.get(var_name, "").strip()
                    logger.info(f"[IMAGE_GEN] OS ENV check for {var_name}: {'YES' if api_key else 'NONE'}")

                if not api_key and provider != "pollinations":
                    if last_error:
                        logger.error(f"[IMAGE_GEN] All rotation keys failed for {provider}. Last error: {last_error}")
                        raise last_error
                    logger.error(f"[IMAGE_GEN] Final check failed. Provider={provider}, KeyManager had keys for: {list(manager._pools.keys()) if 'manager' in locals() else 'N/A'}")
                    # If we still have no key and it's not a free provider, we can't continue
                    raise Exception(f"No API key available for {provider}. Add at least one valid key in Key Manager or .env")

                try:
                    logger.info(f"[IMAGE_GEN] Attempt {attempt}/{max_attempts} via {provider}/{model}")
                    filename = generate_image(
                        prompt=prompt, 
                        provider=provider, 
                        model=model, 
                        width=width, 
                        height=height, 
                        api_key=api_key,
                        negative_prompt=neg_prompt,
                        guidance_scale=guidance,
                        num_inference_steps=steps,
                        auto_enrich=enrich,
                        enrich_keywords=enrich_keywords,
                        style=style
                    )
                    clean_prompt = prompt.strip()[:80]
                    return f"Here is the image of **{clean_prompt}**:\n\n[[IMG:{filename}]]"

                except Exception as e:
                    last_error = e
                    err_msg = str(e)
                    # Check for rate limit, depletion, OOM or loading state
                    # Check for rate limit, depletion, OOM, loading state or server overload/timeout
                    is_retriable = any(x.lower() in err_msg.lower() for x in [
                        "HTTP 402", "HTTP 429", "HTTP 503", "HTTP 500", "HTTP 504",
                        "CUDA out of memory", "Model is loading", 
                        "Rate limit reached", "You have reached your limit",
                        "server is overloaded", "upstream request timeout",
                        "timed out", "timeout"
                    ])
                    
                    if is_retriable:
                        logger.warning(f"[IMAGE_GEN] Key/Server failed ({err_msg}). Marking as exhausted and retrying...")
                        try:
                            from zentra.core.keys.key_manager import get_key_manager
                            manager = get_key_manager()
                            # If it was the pinned key, we should clear it for this session's attempts
                            if api_key == pinned_key:
                                pinned_key = "" 
                            
                            # Mark as exhausted so get_key returns the next one
                            # Reason varies based on error
                            reason = "rate_limited" if ("402" in err_msg or "429" in err_msg) else "server_overload"
                            # If it was a timeout or overload, use a longer cooldown (1 hour) to keep the system responsive
                            cd_sec = 3600 if reason == "server_overload" else 60.0
                            manager.mark_exhausted(provider, api_key, reason=reason, cooldown=cd_sec)
                        except Exception:
                            pass
                        continue # Try next key
                    else:
                        # Other errors (syntax, safety, etc.) should probably not be retried with different keys
                        raise e

            raise last_error or Exception("Max attempts reached without success.")

        except Exception as e:
            logger.error(f"[IMAGE_GEN] Generation failed: {e}")
            # If 'Artist' is already in the message (from the engine), use it as is
            err_str = str(e)
            if "Artist" not in err_str:
                err_str = f"Artist [{provider.capitalize()}] rejected: {err_str}"
            
            return f"⚠️ Image generation failed. {err_str}. Verify provider config or prompt safety."


# Export instance
tools = ImageGenTools()

def info():
    return {"tag": tools.tag, "desc": tools.desc}

def status():
    return tools.status
