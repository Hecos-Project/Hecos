import os, sys
sys.path.insert(0, r'C:\Hecos')
from hecos.core.package_manager.installer import PackageInstaller
from hecos.core.package_manager.registry import PackageRegistry
from hecos.core.system.version import VERSION

registry = PackageRegistry(data_dir=r'C:\Hecos\hecos\data')
installer = PackageInstaller(
    hecos_root=r'C:\Hecos\hecos',
    registry=registry,
    hecos_version=VERSION,
    event_callback=lambda x, y: None
)

packages_to_install = [
    r'C:\Hecos-Packages\packages\calendar-1.0.4.hpkg',
    r'C:\Hecos-Packages\packages\reminder-1.0.3.hpkg',
    r'C:\Hecos-Packages\packages\map-1.0.1.hpkg',
    r'C:\Hecos-Packages\packages\webcam-1.0.2.hpkg',
    r'C:\Hecos-Packages\packages\webcam_feed-1.0.1.hpkg'
]

for pkg in packages_to_install:
    if os.path.exists(pkg):
        with open(pkg, 'rb') as f:
            data = f.read()
        res = installer.install_bytes(data, require_signature=False)
        print(f"Installed {pkg}: success={res.success}, error={res.error}")
    else:
        print(f"Not found: {pkg}")
