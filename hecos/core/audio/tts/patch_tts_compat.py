"""
Hecos compatibility patch for TTS 0.22.0 with transformers 5.x + PyTorch 2.6+

Run this script whenever TTS is reinstalled:
    python hecos/core/audio/tts/patch_tts_compat.py

Or call apply_all_patches() from code.
"""
import re
import sys
import os

TTS_SITE = os.path.join(os.path.dirname(sys.executable), "Lib", "site-packages", "TTS")


def patch_stream_generator():
    """
    Stub stream_generator.py.
    Only init_stream_support() is imported by xtts.py. The streaming inference
    feature is not used in Hecos (tts_to_file is used instead), and the file
    imports many symbols removed from transformers 5.x (BeamSearchScorer,
    SampleOutput, etc.).
    """
    path = os.path.join(TTS_SITE, "tts", "layers", "xtts", "stream_generator.py")
    stub = '''# Hecos compatibility stub — streaming inference disabled for transformers 5.x
def init_stream_support():
    """No-op: streaming inference not used; stubbed for transformers 5.x compat."""
    pass
'''
    with open(path, "w", encoding="utf-8") as f:
        f.write(stub)
    print(f"[OK] stream_generator.py stubbed.")


def patch_io():
    """
    Force weights_only=False on torch.load calls.
    PyTorch 2.6 changed the default to weights_only=True, which blocks XTTS
    checkpoints that embed custom classes (XttsConfig).
    """
    path = os.path.join(TTS_SITE, "utils", "io.py")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    if "weights_only=False" in content:
        print(f"[SKIP] io.py already patched.")
        return

    def _add_weights_only(m):
        inner = m.group(1)
        if "weights_only" in inner:
            return m.group(0)
        return f"return torch.load({inner}, weights_only=False)"

    new_content = re.sub(r"return torch\.load\(([^)]+)\)", _add_weights_only, content)
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"[OK] io.py patched (weights_only=False).")


def patch_gpt_inference():
    """
    Add GenerationMixin to GPT2InferenceModel base classes.
    From transformers v4.50+, GenerationMixin (which provides .generate()) is
    no longer automatically inherited through PreTrainedModel.
    Also fixes vocab_size (for tokenizer padding) and the Transformers 5.x 
    DynamicCache bug that skips conditioning on the first step.
    """
    path = os.path.join(TTS_SITE, "tts", "layers", "xtts", "gpt_inference.py")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    if "DynamicCache" in content and "cache_has_data" in content:
        print(f"[SKIP] gpt_inference.py already patched.")
        return

    content = content.replace(
        "from transformers import GPT2PreTrainedModel",
        (
            "from transformers import GPT2PreTrainedModel\n"
            "try:\n"
            "    from transformers import GenerationMixin\n"
            "except ImportError:\n"
            "    GenerationMixin = object"
        ),
    )
    content = content.replace(
        "class GPT2InferenceModel(GPT2PreTrainedModel):",
        "class GPT2InferenceModel(GPT2PreTrainedModel, GenerationMixin):",
    )
    
    # FIX: Transformers 5.x strictly validates bos_token_id against vocab_size during GenerationConfig init.
    # Must run BEFORE super().__init__ which creates GenerationConfig.
    content = content.replace(
        "super().__init__(config)",
        "if hasattr(config, 'vocab_size') and config.vocab_size < 100000:\n            config.vocab_size = 100000\n        super().__init__(config)"
    )

    # FIX: Transformers 5.x DynamicCache is truthy even when empty, breaking the past_key_values check.
    old_prepare = '''        # only last token for inputs_ids if past is defined in kwargs
        if past_key_values is not None:
            input_ids = input_ids[:, -1].unsqueeze(-1)
            if token_type_ids is not None:
                token_type_ids = token_type_ids[:, -1].unsqueeze(-1)

        attention_mask = kwargs.get("attention_mask", None)
        position_ids = kwargs.get("position_ids", None)

        if attention_mask is not None and position_ids is None:
            # create position_ids on the fly for batch generation
            position_ids = attention_mask.long().cumsum(-1) - 1
            position_ids.masked_fill_(attention_mask == 0, 1)
            if past_key_values is not None:
                position_ids = position_ids[:, -1].unsqueeze(-1)'''
                
    new_prepare = '''        # ── Transformers 5.x compatibility fix ──────────────────────────
        cache_has_data = False
        if past_key_values is not None:
            if hasattr(past_key_values, 'get_seq_length'):
                cache_has_data = past_key_values.get_seq_length() > 0
            elif isinstance(past_key_values, (list, tuple)) and len(past_key_values) > 0:
                cache_has_data = past_key_values[0] is not None
            else:
                cache_has_data = bool(past_key_values)

        if cache_has_data:
            input_ids = input_ids[:, -1].unsqueeze(-1)
            if token_type_ids is not None:
                token_type_ids = token_type_ids[:, -1].unsqueeze(-1)
        else:
            past_key_values = None

        attention_mask = kwargs.get("attention_mask", None)
        position_ids = kwargs.get("position_ids", None)

        if attention_mask is not None and position_ids is None:
            position_ids = attention_mask.long().cumsum(-1) - 1
            position_ids.masked_fill_(attention_mask == 0, 1)
            if cache_has_data:
                position_ids = position_ids[:, -1].unsqueeze(-1)'''

    content = content.replace(old_prepare, new_prepare)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[OK] gpt_inference.py patched (GenerationMixin + vocab_size + DynamicCache).")


def apply_all_patches():
    print("Applying Hecos TTS compatibility patches...")
    patch_stream_generator()
    patch_io()
    patch_gpt_inference()
    print("All patches applied.")


if __name__ == "__main__":
    apply_all_patches()
