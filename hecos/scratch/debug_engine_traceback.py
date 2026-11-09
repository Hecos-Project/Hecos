import sys
import traceback
sys.path.insert(0, '.')

from hecos.hpm.image_gen.plugin.generator import _engine_generate
from hecos.hpm.image_gen.igen_config.config_manager import get_effective_config

cfg = get_effective_config()
print("Provider:", cfg.get("provider"))

try:
    _engine_generate(
        prompt="a photo of a cute kitten",
        provider=cfg.get("provider", "swarmui"),
        model=cfg.get("model", ""),
        width=512,
        height=512,
        api_key="",
        negative_prompt="",
        guidance_scale=7.5,
        num_inference_steps=20,
        seed=-1,
        sampler="",
        scheduler="",
        hf_provider="",
        horde_nsfw=False,
        horde_worker_blacklist="",
        vae="",
        loras=[]
    )
except Exception as e:
    print("Caught exception in _engine_generate:")
    traceback.print_exc()

