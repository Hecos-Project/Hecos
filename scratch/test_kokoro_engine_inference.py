import sys
import os
sys.path.insert(0, r"C:\Hecos")

from hecos.core.audio.tts.kokoro_engine import KokoroEngine

engine = KokoroEngine.get_instance()
out_wav = r"C:\Hecos\scratch\test_engine_speed_blend.wav"

# Test speed 1.4, voice im_voce_antonio_02, blend with im_nicola, alpha 0.8, beta 0.5
success = engine.generate_wav(
    "Test delle variabili di inferenza di Kokoro: velocità accelerata a uno punto quattro con fusione timbrica.",
    out_wav,
    tts_voice="im_voce_antonio_02",
    blend_voice="im_nicola",
    alpha=0.8,
    beta=0.5,
    speed=1.4,
    volume=1.0,
    normalize=True
)

print(f"generate_wav success: {success}, exists: {os.path.exists(out_wav)}, size: {os.path.getsize(out_wav) if os.path.exists(out_wav) else 0}")
