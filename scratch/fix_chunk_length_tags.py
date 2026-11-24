import pathlib

targets = [
    r'C:\Hecos\hecos\hpm\voice_forge\core\engines\fish.py',
    r'C:\Hecos-Elite\sources\apps\voice_forge_src\core\engines\fish.py',
]

OLD = (
    '    eff_text = apply_emotion_cue_if_needed(ref_text, emotion_style)\n'
    '    # ForgePipeline handles pause splitting, chunking, and style propagation cleanly.\n'
    '    overrides["fish_chunk_sentences"] = False\n'
    '    overrides["fish_use_memory_cache"] = True\n'
    '    overrides.update(samp_ov)\n'
    '    if not sampling["preset_locked_max_tokens"]:\n'
    '        overrides["fish_max_new_tokens"] = _estimate_fish_max_tokens(eff_text)\n'
    '    if "normalize" in raw_extra:\n'
    '        overrides["fish_normalize"] = raw_extra["normalize"]'
)

NEW = (
    '    eff_text = apply_emotion_cue_if_needed(ref_text, emotion_style)\n'
    '    # ForgePipeline handles pause splitting, chunking, and style propagation cleanly.\n'
    '    overrides["fish_chunk_sentences"] = False\n'
    '    overrides["fish_use_memory_cache"] = True\n'
    '    overrides.update(samp_ov)\n'
    '    if not sampling["preset_locked_max_tokens"]:\n'
    '        overrides["fish_max_new_tokens"] = _estimate_fish_max_tokens(eff_text)\n'
    '    if "normalize" in raw_extra:\n'
    '        overrides["fish_normalize"] = raw_extra["normalize"]\n'
    '    # When expressive tags are present, ensure Fish Speech internal chunk_length is large\n'
    '    # enough to never split the text mid-sentence. VoiceForge already handles multi-sentence\n'
    '    # splitting upstream; Fish re-splitting at 200 chars causes each internal chunk to lose\n'
    '    # cross-chunk tag context, producing voice drift between [excited]/[whisper]/[laughing].\n'
    '    if count_expressive_tags(eff_text) > 0:\n'
    '        min_chunk = min(1200, len(eff_text) + 80)\n'
    '        if "fish_chunk_length" not in overrides or int(overrides.get("fish_chunk_length", 0)) < min_chunk:\n'
    '            overrides["fish_chunk_length"] = min_chunk'
)

for t in targets:
    p = pathlib.Path(t)
    if not p.exists():
        print(f'NOT FOUND: {t}')
        continue
    text = p.read_text(encoding='utf-8')
    if OLD not in text:
        print(f'ANCHOR NOT FOUND in {t}')
        # Show what's around line 405
        for i, line in enumerate(text.splitlines()[403:415], start=404):
            print(f'  {i}: {line}')
        continue
    new_text = text.replace(OLD, NEW)
    p.write_text(new_text, encoding='utf-8')
    bom = p.read_bytes()[:3] == b'\xef\xbb\xbf'
    ok = 'count_expressive_tags(eff_text) > 0' in new_text
    print(f'FIXED: {t}  BOM:{bom}  patch_ok:{ok}')
