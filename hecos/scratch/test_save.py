import sys
import os
sys.path.insert(0, r"C:\Hecos")

from hecos.core.global_presets.schema import SoulProfile
from hecos.config.yaml_utils import load_yaml, save_yaml

fp = r"C:\Hecos\hecos\config\data\global_presets\experimental_1.global_preset.yaml"
soul = load_yaml(fp, SoulProfile)
print("Before:", soul.inference.preset_name, soul.voice.xtts_inference_preset)

soul.inference.preset_name = "Creative and Wild"
soul.voice.xtts_inference_preset = "Fast and Expressive"

save_yaml(fp, soul)

soul2 = load_yaml(fp, SoulProfile)
print("After:", soul2.inference.preset_name, soul2.voice.xtts_inference_preset)
