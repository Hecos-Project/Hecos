import sys
sys.path.insert(0, r"C:\Hecos")
from hecos.core.package_manager.installer import PackageInstaller
from hecos.core.package_manager.registry import PackageRegistry

registry = PackageRegistry(r"C:\Hecos\hecos\config\data")
installer = PackageInstaller(r"C:\Hecos\hecos", registry)
result = installer.install_file(r"C:\Hecos-Packages\image_gen-1.0.8.hpkg", require_signature=False)
print("Install result:", result)
