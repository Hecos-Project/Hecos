import sys
sys.path.insert(0, r'C:\Hecos')
from hecos.core.package_manager.registry import PackageRegistry

registry = PackageRegistry(r'C:\Hecos\hecos\data')
pkgs = registry.list_all()
print(f'Total packages found in DB: {len(pkgs)}')
for p in pkgs:
    print(f'- {p["id"]} (v{p["version"]})')
    manifest = p.get("manifest_snapshot", {})
    print(f'  Has capabilities? {"Yes" if "capabilities" in manifest else "No"}')
