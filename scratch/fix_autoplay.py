import pathlib

targets = [
    r'C:\Hecos\hecos\hpm\voice_forge\web\static\js\vf_production.js',
    r'C:\Hecos-Elite\sources\apps\voice_forge_src\web\static\js\vf_production.js',
]

OLD_PRELOAD = '        audio.preload = "none";'
NEW_PRELOAD = '        audio.preload = this.isAutoPlayEnabled() ? "auto" : "none";'

OLD_TIMEOUT = '''    setTimeout(() => {
      const audio = card.querySelector(".vf-take-audio");
      if (!audio) return;
      audio.currentTime = 0;
      const tryPlay = () => audio.play().catch(e => console.log("[VoiceForge] Auto-play prevented by browser policy:", e));
      if (audio.readyState >= 2) {
        tryPlay();
      } else {
        audio.addEventListener("canplay", tryPlay, { once: true });
      }
    }, 80);'''

NEW_TIMEOUT = '''    // Give the browser a moment to fetch the audio (preload=auto was set in renderTakes),
    // then play. If still not ready, attach canplay listener + force load() as fallback.
    const doPlay = () => {
      const audio = card.querySelector(".vf-take-audio");
      if (!audio) return;
      audio.currentTime = 0;
      const tryPlay = () => audio.play().catch(e => console.log("[VoiceForge] Auto-play prevented by browser policy:", e));
      if (audio.readyState >= 2) {
        tryPlay();
      } else {
        audio.addEventListener("canplay", tryPlay, { once: true });
        // Force load in case preload=auto hasn't kicked in yet
        audio.load();
      }
    };
    setTimeout(doPlay, 150);'''

for t in targets:
    p = pathlib.Path(t)
    text = p.read_text(encoding='utf-8')
    orig = text

    text = text.replace(OLD_PRELOAD, NEW_PRELOAD)
    text = text.replace(OLD_TIMEOUT, NEW_TIMEOUT)

    if text == orig:
        print(f'NO CHANGE in {t}')
        # Debug: check if old strings are present
        print(f'  OLD_PRELOAD found: {OLD_PRELOAD in orig}')
        print(f'  OLD_TIMEOUT found: {OLD_TIMEOUT in orig}')
    else:
        p.write_text(text, encoding='utf-8')
        bom = p.read_bytes()[:3] == b'\xef\xbb\xbf'
        print(f'FIXED: {t}')
        print(f'  preload->auto: {NEW_PRELOAD in text}  audio.load(): {"audio.load()" in text}  BOM:{bom}')
