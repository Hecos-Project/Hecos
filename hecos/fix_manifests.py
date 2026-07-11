import os
import re
import glob
import shutil

base_dir = r"C:\Hecos-Packages"
count = 0

for toml_path in glob.glob(os.path.join(base_dir, "*_src", "hpkg_manifest.toml")):
    with open(toml_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    original_content = content
    
    # 1. Remove all pip_isolation lines completely
    content = re.sub(r'^[ \t]*pip_isolation[ \t]*=[ \t]*"[^"]*"[ \t]*\n?', '', content, flags=re.MULTILINE)
    
    # 2. Add pip_isolation = "shared" (or "isolated" for image_gen) right after type = "..."
    isolation_mode = "isolated" if "image_gen_src" in toml_path else "shared"
    
    content = re.sub(r'^(type[ \t]*=[ \t]*"[^"]*"\n)', f'\\1pip_isolation = "{isolation_mode}"\n', content, count=1, flags=re.MULTILINE)
    
    if content != original_content:
        # Save a backup just in case
        # shutil.copy2(toml_path, toml_path + ".bak")
        with open(toml_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Fixed {toml_path}")
        count += 1
        
        # ALSO update the live version if it exists
        live_dir = os.path.basename(os.path.dirname(toml_path)).replace("_src", "")
        live_path = os.path.join(r"C:\Hecos\hecos\hpm", live_dir, "hpkg_manifest.toml")
        if os.path.exists(live_path):
            with open(live_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"  -> Synced to live {live_path}")

print(f"Done. Fixed {count} manifests.")
