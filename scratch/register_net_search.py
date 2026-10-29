import sys
import os
sys.path.insert(0, r"c:\Hecos")

try:
    import tomllib
except ImportError:
    import tomli as tomllib

from hecos.core.package_manager.registry import PackageRegistry

manifest_path = r"c:\Hecos\hecos\modules\net_search\hpkg_manifest.toml"
with open(manifest_path, "rb") as f:
    manifest = tomllib.load(f)

reg = PackageRegistry(r"c:\Hecos\hecos\data")
ok = reg.register(manifest, r"hecos\modules\net_search")
print("Registered net_search in PackageRegistry:", ok)

pkg = reg.get("net_search")
print("Verified package:", pkg["id"], pkg["name"], pkg["type"], pkg["status"])
