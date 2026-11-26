"""
Build + deploy script for Voice Forge.
Builds voice_forge-X.Y.Z.hpkg from Hecos-Elite sources and deploys it live into Hecos.

Usage:
    C:\\Hecos\\python_env\\python.exe C:\\Hecos\\scratch\\build_voice_forge.py
"""
import sys
import os
import shutil
import zipfile
import time
from pathlib import Path

# --- Paths ---
BUILDER_DIR  = Path(r"C:\Hecos-Packages\Hecos_HPM_Builder")
SRC_DIR      = Path(r"C:\Hecos-Elite\sources\apps\voice_forge_src")
# The HPM builder places the .hpkg in a sub-folder named after the source's parent
# (voice_forge_src lives under "apps", so output goes to packages/apps/apps/).
# We pass the grandparent so the builder lands the file in packages/apps/ directly.
OUT_DIR_BASE = Path(r"C:\Hecos-Elite\packages")
DEPLOY_DIR   = Path(r"C:\Hecos\hecos\hpm\voice_forge")
LIVEBACKUP   = Path(r"C:\Hecos-Elite\livebackup")

# Add builder to sys.path and chdir so relative imports inside builder work
sys.path.insert(0, str(BUILDER_DIR))
os.chdir(BUILDER_DIR)

from modules.settings import load_config
load_config()
from modules.builder import _build_single_package

# Build — output lands in OUT_DIR_BASE/apps/voice_forge-X.Y.Z.hpkg
OUT_DIR_BASE.mkdir(parents=True, exist_ok=True)
print(f"Building voice_forge from: {SRC_DIR}")
print(f"Builder output base: {OUT_DIR_BASE}")

result = _build_single_package(SRC_DIR, OUT_DIR_BASE)

if not result:
    print("Build FAILED.")
    sys.exit(1)

# Find the freshly built .hpkg (search recursively — builder may nest it)
all_hpkgs = sorted(
    OUT_DIR_BASE.rglob("voice_forge-*.hpkg"),
    key=lambda p: p.stat().st_mtime,
    reverse=True
)
if not all_hpkgs:
    print("ERROR: No voice_forge-*.hpkg found after build.")
    sys.exit(1)

latest = all_hpkgs[0]
print(f"\nBuilt: {latest} ({latest.stat().st_size / 1024:.1f} KB)")

# Normalize location: move to packages/apps/ if it landed deeper
expected = OUT_DIR_BASE / "apps" / latest.name
if latest != expected:
    expected.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(latest), str(expected))
    # Clean up empty leftover dirs
    try:
        latest.parent.rmdir()
    except Exception:
        pass
    latest = expected
    print(f"Moved to canonical location: {latest}")

# Remove older versions of the same package
for old in (OUT_DIR_BASE / "apps").glob("voice_forge-*.hpkg"):
    if old != latest:
        old.unlink()
        print(f"Removed old: {old.name}")

# Backup current live deploy
if DEPLOY_DIR.exists():
    ts = time.strftime("%Y%m%d_%H%M%S")
    backup = LIVEBACKUP / f"voice_forge_{ts}"
    shutil.copytree(DEPLOY_DIR, backup, dirs_exist_ok=True)
    print(f"\nBacked up current install → livebackup/voice_forge_{ts}")

# Deploy: unpack hpkg into Hecos hpm/voice_forge (including signed hpkg_manifest.toml)
DEPLOY_DIR.mkdir(parents=True, exist_ok=True)
print(f"Deploying to: {DEPLOY_DIR}")
with zipfile.ZipFile(latest, 'r') as zf:
    members = list(zf.namelist())
    for member in members:
        dest = DEPLOY_DIR / member
        dest.parent.mkdir(parents=True, exist_ok=True)
        with zf.open(member) as src_f, open(dest, 'wb') as dst_f:
            dst_f.write(src_f.read())

print(f"Deployed {len(members)} files")

# Read version from manifest for the success message
try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

version = "?"
if tomllib:
    try:
        with zipfile.ZipFile(latest, 'r') as zf:
            toml_bytes = zf.read("hpkg_manifest.toml")
        version = tomllib.loads(toml_bytes.decode("utf-8")).get("version", "?")
    except Exception:
        pass

# Post-deploy: strip BOM from any text files that may have gotten one
# (PowerShell Set-Content -Encoding UTF8 adds BOM; we strip it here defensively)
BOM = b'\xef\xbb\xbf'
stripped = 0
for ext in ('*.html', '*.js', '*.css', '*.py', '*.json', '*.toml'):
    for fpath in DEPLOY_DIR.rglob(ext):
        raw = fpath.read_bytes()
        if raw.startswith(BOM):
            fpath.write_bytes(raw[len(BOM):])
            stripped += 1
if stripped:
    print(f"Stripped UTF-8 BOM from {stripped} file(s)")

print(f"\n✅ Voice Forge v{version} built, signed and deployed to live Hecos.")
print(f"   hpkg: {latest.name}")
print(f"   Restart Hecos to apply changes.")
