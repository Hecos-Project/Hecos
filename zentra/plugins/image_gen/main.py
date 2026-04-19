"""
Plugin: Image Generation
Delegates image generation to core/media/image_providers.py (multi-provider engine).
"""
try:
    from zentra.core.logging import logger
    from zentra.core.media_config import get_media_config
    from zentra.core.media.image_providers import generate_image, get_models_for_provider
    from zentra.core.i18n import translator
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

    def _refine_flux_prompt(self, original_prompt: str, instructions: str) -> str:
        """Uses Zentra's Brain to refine the prompt for Flux."""
        try:
            from zentra.core.llm import client
            from zentra.core.media_config import get_media_config
            from zentra.app.config import ConfigManager
            import json
            
            # Use main system config for LLM call
            main_cfg = ConfigManager().config
            
            system_prompt = (
                "You are an expert prompt engineer specializing in the Flux image generation model. "
                "Flux prefers detailed, natural language descriptions over comma-separated tags. "
                f"{instructions}"
            )
            
            user_msg = f"Optimize this prompt for Flux: {original_prompt}"
            
            # Grab effective backend
            from app.model_manager import ModelManager
            effective_backend_type, effective_default_model = ModelManager.get_effective_model_info(main_cfg)
            backend_config = main_cfg.get('backend', {}).get(effective_backend_type, {}).copy()
            backend_config['model'] = effective_default_model
            backend_config['backend_type'] = effective_backend_type
            
            llm_cfg = main_cfg.get('llm', {})
            
            logger.info(f"[IMAGE_GEN] Refining prompt for Flux via {effective_backend_type}...")
            
            refined = client.generate(system_prompt, user_msg, backend_config, llm_cfg)
            
            if refined and not isinstance(refined, dict) and not refined.startswith("⚠️"):
                # Clean up quotes if the model wrapped it
                cleaned = refined.strip().strip('"').strip("'")
                logger.info(f"[IMAGE_GEN] Flux prompt refined successfully: {cleaned[:50]}...")
                return cleaned
            
            logger.warning("[IMAGE_GEN] LLM returned empty or error, falling back to original prompt.")
            return original_prompt
                
        except Exception as e:
            logger.error(f"[IMAGE_GEN] Brain refinement failed: {e}")
            return original_prompt

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
            
            use_neg_prompt = cfg.get("enable_negative_prompt", True)
            neg_prompt = cfg.get("negative_prompt", "") if use_neg_prompt else ""
            
            guidance   = float(cfg.get("guidance_scale", 7.5))
            steps      = int(cfg.get("num_inference_steps", 30))
            
            # Flux Optimization Logic
            optimize_flux = cfg.get("optimize_for_flux", True)
            flux_instructions = cfg.get("flux_refiner_instructions", "Convert keywords into a descriptive natural language paragraph for Flux. Output ONLY the optimized prompt, no preamble.")
            
            if optimize_flux and "flux" in model.lower():
                logger.info("[IMAGE_GEN] Flux optimization requested. Calling Brain refiner...")
                prompt = self._refine_flux_prompt(prompt, flux_instructions)
                enrich = False # Disable legacy tag injection for Flux
            else:
                enrich = cfg.get("auto_enrich", True)
            
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
                    # Increased limit from 80 to 256 to avoid truncation. 
                    # Use ellipsis if still too long.
                    clean_prompt = prompt.strip()
                    if len(clean_prompt) > 250:
                        clean_prompt = clean_prompt[:247] + "..."
                    
                    prefix = translator.t("igen_response_prefix", prompt=clean_prompt)
                    return f"{prefix}\n\n[[IMG:{filename}]]"

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
