import sys, os
sys.path.insert(0, r'c:\Hecos')

print('HPM modules with routes:')
from hecos.core.package_manager.registry import PackageRegistry
reg = PackageRegistry(r'c:\Hecos\hecos\hpm\data')
for pkg in reg.list_all():
    man = pkg.get('manifest_snapshot', {})
    if isinstance(man, str): 
        import json
        try: man = json.loads(man)
        except: pass
    cp = man.get('config_panel', {})
    if cp.get('api_routes_file'):
        print(f"  {pkg['id']} -> {cp['api_routes_file']} (install path: {pkg.get('install_path')})")
