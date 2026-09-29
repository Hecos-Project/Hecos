import sys
import os
sys.path.insert(0, r"C:\Hecos")

from hecos.core.global_presets import list_inference_presets

p = list_inference_presets()
print(list(p.keys()))
