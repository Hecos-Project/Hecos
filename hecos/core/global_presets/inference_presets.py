"""
hecos/core/global_presets/inference_presets.py
CRUD per Inference Presets (balanced, creative, precise, ecc.)
"""

import os
from typing import Dict, Optional
from hecos.core.logging import logger
from hecos.config import load_yaml, save_yaml
from hecos.core.constants import CONFIG_DATA_DIR
from hecos.core.global_presets.schema import InferencePresetsFile, InferencePreset

PRESETS_PATH = os.path.join(CONFIG_DATA_DIR, "inference_presets.yaml")

DEFAULT_PRESETS = {
    "balanced": InferencePreset(
        temperature=0.7, top_p=0.9, repeat_penalty=1.1, num_predict=1024,
        description="Balanced for general use"
    ),
    "creative": InferencePreset(
        temperature=0.95, top_p=0.98, repeat_penalty=1.0, num_predict=2048,
        description="High creativity, low repetition"
    ),
    "precise": InferencePreset(
        temperature=0.2, top_p=0.8, repeat_penalty=1.3, num_predict=512,
        description="Precise and concise responses"
    ),
    "roleplay": InferencePreset(
        temperature=0.85, top_p=0.92, repeat_penalty=1.05, num_predict=4096,
        description="Optimized for immersive roleplay"
    ),
    "uncensored_max": InferencePreset(
        temperature=1.5, top_p=0.99, repeat_penalty=0.9, num_predict=4096,
        description="Maximum creative freedom, zero filters"
    )
}

def list_inference_presets() -> Dict[str, InferencePreset]:
    if not os.path.exists(PRESETS_PATH):
        # Create default
        model = InferencePresetsFile(presets=DEFAULT_PRESETS)
        save_yaml(PRESETS_PATH, model)
        return model.presets
        
    try:
        model = load_yaml(PRESETS_PATH, InferencePresetsFile)
        # Ensure defaults exist if file is empty
        if not model.presets:
            model.presets = DEFAULT_PRESETS
            save_yaml(PRESETS_PATH, model)
        return model.presets
    except Exception as e:
        logger.error(f"[GlobalPresets] Error loading inference presets: {e}")
        return DEFAULT_PRESETS

def save_inference_preset(name: str, preset: InferencePreset) -> bool:
    presets = list_inference_presets()
    presets[name] = preset
    model = InferencePresetsFile(presets=presets)
    return save_yaml(PRESETS_PATH, model)

def delete_inference_preset(name: str) -> bool:
    presets = list_inference_presets()
    if name in presets:
        del presets[name]
        model = InferencePresetsFile(presets=presets)
        return save_yaml(PRESETS_PATH, model)
    return False

def get_inference_preset(name: str) -> Optional[InferencePreset]:
    presets = list_inference_presets()
    return presets.get(name)
