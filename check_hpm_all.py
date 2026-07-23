import sys, os
sys.path.insert(0, r'c:\Hecos')

print('All HPM modules:')
from hecos.core.package_manager.registry import PackageRegistry
reg = PackageRegistry(r'c:\Hecos\hecos\data')
for pkg in reg.list_all():
    print(f"  {pkg['id']} (install path: {pkg.get('install_path')})")
