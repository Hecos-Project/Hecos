import subprocess
from pathlib import Path
import shutil

ELITE_DIR = Path(r"C:\Hecos-Elite")
SRC_TEMPLATE = ELITE_DIR / "sources" / "apps" / "voice_forge_src" / "web" / "templates" / "config_voice_forge.html"
LIVE_HPM_TEMPLATE = Path(r"C:\Hecos\hecos\hpm\voice_forge\web\templates\config_voice_forge.html")
LIVE_MODULE_TEMPLATE = Path(r"C:\Hecos\hecos\modules\web_ui\templates\modules\config_voice_forge.html")

# 1. Restore pristine template from git commit dd3200c
print("Restoring clean template from git commit dd3200c...")
subprocess.run(
    ["git", "checkout", "dd3200c", "--", str(SRC_TEMPLATE)],
    cwd=str(ELITE_DIR),
    check=True
)

# 2. Read with utf-8, replace v=1.3.4 with v=1.3.5, save as strict utf-8 without BOM
content = SRC_TEMPLATE.read_text(encoding="utf-8")
print(f"Read {len(content)} chars. Checking pristine content...")
assert "Fran\xe7ais" in content, "Failed to find 'Français' in restored template!"
assert "Espa\xf1ol" in content, "Failed to find 'Español' in restored template!"
assert "\u25cf" in content, "Failed to find black circle in restored template!"
assert "\xb7" in content, "Failed to find middle dot in restored template!"

content = content.replace("?v=1.3.4", "?v=1.3.5")
SRC_TEMPLATE.write_text(content, encoding="utf-8")
print("Template updated to v=1.3.5 without BOM.")

# 3. Copy to live paths
LIVE_HPM_TEMPLATE.parent.mkdir(parents=True, exist_ok=True)
LIVE_MODULE_TEMPLATE.parent.mkdir(parents=True, exist_ok=True)

LIVE_HPM_TEMPLATE.write_text(content, encoding="utf-8")
LIVE_MODULE_TEMPLATE.write_text(content, encoding="utf-8")
print("Synced template to live hpm and live modules paths.")

# 4. Sync JS files from sources to modules/web_ui and hpm
SRC_JS_DIR = ELITE_DIR / "sources" / "apps" / "voice_forge_src" / "web" / "static" / "js"
HPM_JS_DIR = Path(r"C:\Hecos\hecos\hpm\voice_forge\web\static\js")
WEBUI_JS_DIR = Path(r"C:\Hecos\hecos\modules\web_ui\static\js")

for js_file in SRC_JS_DIR.glob("*.js"):
    shutil.copy2(js_file, HPM_JS_DIR / js_file.name)
    shutil.copy2(js_file, WEBUI_JS_DIR / js_file.name)
print(f"Synced {len(list(SRC_JS_DIR.glob('*.js')))} JS files across all paths.")

# Verify no mojibake in any of the templates
for path in [SRC_TEMPLATE, LIVE_HPM_TEMPLATE, LIVE_MODULE_TEMPLATE]:
    txt = path.read_text(encoding="utf-8")
    for bad in ["â—", "Â·", "FranÃ§ais", "EspaÃ±ol", "â€”"]:
        if bad in txt:
            raise RuntimeError(f"Mojibake token '{bad}' found in {path}!")
print("Verification passed: ALL templates are 100% clean UTF-8.")
