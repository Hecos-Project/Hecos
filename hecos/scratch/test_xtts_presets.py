import sys
sys.path.insert(0, r"C:\Hecos")
from hecos.core.audio.config_audio import load_audio_config
config = load_audio_config()
print(list(config.xtts_inference_presets.keys()))
