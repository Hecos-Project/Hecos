import shutil
import os

# Source artifact directory
src_dir = r"C:\Users\Asus\.gemini\antigravity\brain\60d83b6f-1813-4d07-aa3e-7676bef5ed14"
# Target assets directory
target_dir = r"c:\Hecos\hecos\assets"

assets_to_deploy = [
    ("hecos_logo_modern_1777541396946.png", "Hecos_Logo.jpg"), # Using PNG as JPG (renaming content)
    ("hecos_logo_transparent_1777542281036.png", "Hecos_Logo_NBG.png"),
    ("hecos_logo_transparent_1777542281036.png", "Hecos_Logo_NBG - SQR.png")
]

if not os.path.exists(target_dir):
    os.makedirs(target_dir, exist_ok=True)

for src_name, target_name in assets_to_deploy:
    src_path = os.path.join(src_dir, src_name)
    target_path = os.path.join(target_dir, target_name)
    
    if os.path.exists(src_path):
        try:
            shutil.copy2(src_path, target_path)
            print(f"Deployed: {src_name} -> {target_name}")
        except Exception as e:
            print(f"Error deploying {src_name}: {e}")
    else:
        print(f"Source not found: {src_path}")

print("Asset deployment check complete.")
