import sys
import os
sys.path.insert(0, r"C:\Hecos")

print("=== 1. Testing AudioConfig schema validation ===")
from hecos.core.audio.device_manager import get_audio_config
cfg = get_audio_config()
kokoro_cfg = cfg.get("kokoro", {})
print("Loaded kokoro config keys:", list(kokoro_cfg.keys()))
assert "speed" in kokoro_cfg
assert "lang_code" in kokoro_cfg
assert "blend_voice" in kokoro_cfg
assert "alpha" in kokoro_cfg
assert "beta" in kokoro_cfg
assert "sentence_silence" in kokoro_cfg
assert "kokoro_inference_presets" in cfg
print("Preses detected:", list(cfg["kokoro_inference_presets"].keys()))

print("\n=== 2. Testing KokoroEngine Inference & Blending ===")
from hecos.core.audio.tts.kokoro_engine import get_engine
engine = get_engine()

out_wav_fast = r"C:\Hecos\scratch\test_kokoro_speed_1_5.wav"
out_wav_blend = r"C:\Hecos\scratch\test_kokoro_blend_nicola_antonio.wav"

# Test Fast speed
ok1 = engine.generate_wav(
    "Questo è un test ad alta velocità con Kokoro impostato a uno punto cinque.",
    out_wav_fast,
    tts_voice="im_nicola",
    speed=1.5
)
print("Speed 1.5x test:", ok1, "File size:", os.path.getsize(out_wav_fast) if os.path.exists(out_wav_fast) else 0)

# Test Voice Blending (im_voce_antonio_02 with im_nicola, alpha=0.7, beta=0.4)
ok2 = engine.generate_wav(
    "Questo è un test di fusione vocale con Antonio e Nicola, bilanciamento alfa e beta.",
    out_wav_blend,
    tts_voice="im_voce_antonio_02",
    blend_voice="im_nicola",
    alpha=0.7,
    beta=0.4,
    speed=1.2
)
print("Blending test:", ok2, "File size:", os.path.getsize(out_wav_blend) if os.path.exists(out_wav_blend) else 0)

print("\n=== 3. Testing TTSCache Key Discrimination ===")
from hecos.core.audio.tts_cache import TTSCache
cache = TTSCache.get_instance()
k1 = cache._extract_voice_and_params("kokoro", {"tts_voice": "im_nicola", "speed": 1.0, "alpha": 1.0})
k2 = cache._extract_voice_and_params("kokoro", {"tts_voice": "im_nicola", "speed": 1.5, "alpha": 1.0})
k3 = cache._extract_voice_and_params("kokoro", {"tts_voice": "im_nicola", "speed": 1.0, "blend_voice": "if_sara", "alpha": 0.5})

print("Cache params k1 (speed 1.0):", k1)
print("Cache params k2 (speed 1.5):", k2)
print("Cache params k3 (blend):", k3)
assert k1 != k2
assert k1 != k3
print("All TTSCache parameter hashes discriminate accurately!")

print("\nALL VERIFICATIONS PASSED SUCCESSFULLY!")
