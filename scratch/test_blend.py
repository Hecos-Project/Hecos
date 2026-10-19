import sys
import os
sys.path.insert(0, r"C:\Hecos")

import torch
from kokoro import KPipeline
from hecos.core.audio.tts.kokoro.voice_manager import KokoroVoiceManager

p = KPipeline(lang_code='i')
pack1, lang1 = KokoroVoiceManager.resolve_voice_pack('im_voce_antonio_02')
pack2 = p.load_voice('im_nicola')

print('pack1 shape:', pack1.shape, 'pack2 shape:', pack2.shape)
alpha = 0.8
beta = 0.5
blended = torch.zeros_like(pack1)
blended[:, :, :128] = alpha * pack1[:, :, :128] + (1.0 - alpha) * pack2[:, :, :128]
blended[:, :, 128:] = beta * pack1[:, :, 128:] + (1.0 - beta) * pack2[:, :, 128:]

res = list(p('Test di sintesi con fusione timbrica e prosodica.', voice=blended, speed=1.15))
print('Chunks count:', len(res))
for _, _, a in res:
    print('Audio length:', len(a) if a is not None else 0)
