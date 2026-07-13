import os
import sys
from pathlib import Path

PACKAGES_ROOT = Path(r"C:\Hecos-Packages")
BUILDER_DIR   = PACKAGES_ROOT / "Hecos_HPM_Builder"
OUTPUT_DIR    = PACKAGES_ROOT / "packages"

sys.path.insert(0, str(BUILDER_DIR))
from modules.settings import load_config
from modules.builder import _build_single_package

load_config()
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

for src_dir in sorted(PACKAGES_ROOT.iterdir()):
    if src_dir.is_dir() and src_dir.name.endswith("_src"):
        print(f"Building {src_dir.name}...")
        _build_single_package(src_dir, OUTPUT_DIR)

print("All packages built successfully.")
