import os
import re
import sys

target_dir = r"C:\Zentra-Core\zentra"
count = 0

print("Starting fix imports script...", flush=True)
try:
    for root, _, files in os.walk(target_dir):
        for f in files:
            if f.endswith('.py'):
                path = os.path.join(root, f)
                try:
                    with open(path, 'r', encoding='utf-8') as file:
                        content = file.read()
                    
                    # Use \b to handle indentation spaces before from/import
                    new_content = re.sub(r'\b(from|import)\s+core\.', r'\1 zentra.core.', content)
                    
                    if new_content != content:
                        with open(path, 'w', encoding='utf-8') as file:
                            file.write(new_content)
                        count += 1
                        print(f"Updated: {path}", flush=True)
                except Exception as e:
                    print(f"Error reading/writing {path}: {e}", flush=True)

    print(f"Total files updated: {count}", flush=True)
except Exception as main_e:
    print(f"CRITICAL ERROR: {main_e}", flush=True)
