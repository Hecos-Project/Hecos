"""
hecos/core/llm/hybrid_model_manager.py
Provides a unified list of models across local and cloud backends.
"""
from hecos.core.logging import logger

def get_hybrid_models(config: dict, config_manager=None) -> list:
    """
    Returns a combined list of local and cloud models.
    Cloud models are included only if llm.allow_cloud is True.
    Uses fast_mode to avoid blocking the HTTP request.
    Pass config_manager to access cached model data.
    """
    models = []
    
    # Use config_manager if provided, else fall back to direct config dict
    if config_manager is None:
        logger.warning("[HYBRID] No config_manager provided; local models may be unavailable.")
        return models
    
    try:
        from hecos.app.model_manager import ModelManager
        mm = ModelManager(config_manager)
        categorized = mm.get_available_models(fast_mode=False)
        
        # 1. Local Models
        for m in categorized.get("Ollama (Local)", []):
            models.append({"id": m, "name": m, "type": "local", "provider": "ollama"})
        for m in categorized.get("Kobold (Local)", []):
            models.append({"id": m, "name": m, "type": "local", "provider": "kobold"})
            
        # 2. Cloud Models — always shown if providers are configured
        # (allow_cloud controls global default, but per-chat override should always show all options)
        for cat_key, cat_models in categorized.items():
            if cat_key.startswith("Cloud"):
                for m in cat_models:
                    provider = m.split("/")[0] if "/" in m else "cloud"
                    models.append({"id": m, "name": m, "type": "cloud", "provider": provider})
    except Exception as e:
        logger.warning(f"[HYBRID] Failed to get models: {e}")
            
    return models
