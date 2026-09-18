import os
from hecos.core.logging import logger

def get_models_dir():
    # Resolves to hecos/models/gguf
    hecos_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
    gguf_dir = os.path.join(hecos_root, "models", "gguf")
    os.makedirs(gguf_dir, exist_ok=True)
    return gguf_dir

def get_available_gguf_models():
    """Returns a dictionary mapping display names (with size) to .gguf model filenames."""
    models = {}
    gguf_dir = get_models_dir()
    try:
        if os.path.exists(gguf_dir):
            for filename in os.listdir(gguf_dir):
                if filename.lower().endswith(".gguf"):
                    filepath = os.path.join(gguf_dir, filename)
                    size_gb = os.path.getsize(filepath) / (1024 ** 3)
                    display_name = f"{filename} ({size_gb:.1f} GB)"
                    models[display_name] = filename
    except Exception as e:
        logger.error(f"[LlamaCPP] Error scanning models dir: {e}")
    return models

def get_model_path(model_filename: str):
    """Returns the absolute path to a specific model."""
    if not model_filename:
        return None
    # Security: prevent directory traversal
    safe_name = os.path.basename(model_filename)
    path = os.path.join(get_models_dir(), safe_name)
    if os.path.exists(path):
        return path
    return None
