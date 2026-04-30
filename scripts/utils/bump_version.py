import os
import re

# Centralized configuration
TARGET_DIR = r"C:\Hecos-Core"
VERSION_FILE = os.path.join(TARGET_DIR, "hecos", "core", "version")
OLD_VERSION = "0.15.2"  # The version to replace

def get_current_version():
    if os.path.exists(VERSION_FILE):
        with open(VERSION_FILE, 'r', encoding='utf-8') as f:
            return f.read().strip()
    return "0.0.0"

NEW_VERSION = get_current_version()
print(f"--- Hecos Version Bumper ---")
print(f"Targeting: {OLD_VERSION} -> {NEW_VERSION}")

# Fixes for common paths
PATH_FIXES = {
    "main/hecos/assets/Hecos_Core_Logo.jpg": "main/hecos/assets/Hecos_Core_Logo.jpg",
    "main/hecos/assets/Hecos_Core_Logo_NBG.png": "main/hecos/assets/Hecos_Core_Logo_NBG.png"
}

count = 0

for root, _, files in os.walk(TARGET_DIR):
    if any(d in root for d in ['venv', '.git', 'node_modules', 'tmp', '__pycache__', 'logs']):
        continue
    for f in files:
        if f.endswith(('.md', '.py', '.toml', '.html')) or f == 'version':
            path = os.path.join(root, f)
            try:
                with open(path, 'r', encoding='utf-8') as file:
                    content = file.read()
                
                # Replace version
                new_content = content.replace(OLD_VERSION, NEW_VERSION)
                
                # Apply path fixes (logo, etc)
                for old_p, new_p in PATH_FIXES.items():
                    new_content = new_content.replace(old_p, new_p)
                
                if new_content != content:
                    with open(path, 'w', encoding='utf-8') as file:
                        file.write(new_content)
                    count += 1
                    print(f"Updated: {os.path.relpath(path, TARGET_DIR)}")
            except Exception as e:
                print(f"Error updating {path}: {e}")

print(f"--- Done! Total files updated: {count} ---")
