import os
import re

hpm_dir = r"C:\Hecos\hecos\hpm"
count = 0

for root, _, files in os.walk(hpm_dir):
    if "manifest.json" in files:
        path = os.path.join(root, "manifest.json")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            
        new_content = re.sub(r'\s*"pip_isolation"\s*:\s*"[^"]*",?', '', content)
        
        if new_content != content:
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)
            count += 1
            print(f"Fixed {path}")

print(f"Done. Fixed {count} files.")
