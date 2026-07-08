import os
import sys

hecos_root = r"C:\Hecos"
if hecos_root not in sys.path:
    sys.path.insert(0, hecos_root)

from hecos.app.config import ConfigManager
from hecos.core.package_manager.installer import PackageInstaller
from hecos.core.package_manager.registry import PackageRegistry

cfg_mgr = ConfigManager()
registry = PackageRegistry(data_dir=r"C:\Hecos\hecos\data")
installer = PackageInstaller(hecos_root=hecos_root, registry=registry, cfg_mgr=cfg_mgr)
result = installer.install_file(r"C:\Hecos-Packages\packages\image_gen-1.0.8.hpkg", require_signature=False)
print("Success:", result.success)
print("Error:", result.error)
print("Warnings:", result.warnings)
