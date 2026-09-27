
import os
from pathlib import Path
try:
    import tomllib
except ImportError:
    import tomli as tomllib
import tomli_w
from hecos.core.package_builder.logger import info, error

def load_manifest(src_dir: str) -> dict:
    manifest_path = Path(src_dir) / "hpkg_manifest.toml"
    if not manifest_path.exists():
        return {}
    try:
        return tomllib.loads(manifest_path.read_bytes().decode("utf-8"))
    except Exception as e:
        error(f"Error reading manifest: {e}")
        return {}

def save_manifest(src_dir: str, data: dict) -> bool:
    manifest_path = Path(src_dir) / "hpkg_manifest.toml"
    try:
        manifest_path.write_bytes(tomli_w.dumps(data).encode("utf-8"))
        return True
    except Exception as e:
        error(f"Error saving manifest: {e}")
        return False

import shutil

def list_preview_images(src_dir: str) -> list:
    src_path = Path(src_dir)
    if not src_path.exists():
        return []
    
    images = []
    # Check preview.png, preview_1.png, preview_2.png, etc.
    for p in src_path.glob("preview*.png"):
        images.append(p.name)
    return sorted(images)

def add_preview_image(src_dir: str, image_path: str) -> str:
    src_path = Path(src_dir)
    img_path = Path(image_path)
    
    if not img_path.exists() or not img_path.is_file():
        raise Exception("Source image does not exist.")
        
    existing = list_preview_images(src_dir)
    next_idx = len(existing) + 1
    new_name = f"preview_{next_idx}.png"
    
    dest_path = src_path / new_name
    shutil.copy2(img_path, dest_path)
    
    info(f"Added preview image {new_name} to {src_dir}")
    return new_name
