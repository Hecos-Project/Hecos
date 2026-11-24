import json, pathlib, sys
sys.path.insert(0, r'C:\Hecos')

d = pathlib.Path(r'C:\Hecos\hecos\hpm\voice_forge\presets\fish_native')
for f in sorted(d.glob('*.json')):
    data = json.loads(f.read_text(encoding='utf-8'))
    spk = data.get('source_speaker') or ''
    preset = data.get('source_preset') or ''
    seed = data.get('source_seed')
    print(f"{f.name}:")
    print(f"  source_speaker: {spk!r}")
    print(f"  source_preset:  {preset!r}")
    print(f"  source_seed:    {seed}")
    print()

from hecos.hpm.voice_forge.library.storage import HECOS_VOICE_CLONES_DIR
print(f"\nCLONES_DIR: {HECOS_VOICE_CLONES_DIR}")
print("Files in voice_clones:")
for f in sorted(HECOS_VOICE_CLONES_DIR.iterdir()):
    print(f"  {f.name}  ({f.stat().st_size} bytes)")
