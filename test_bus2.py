import os, sys
hecos_root = r'C:\Hecos'
if hecos_root not in sys.path:
    sys.path.insert(0, hecos_root)

from hecos.app.config import ConfigManager
cfg = ConfigManager()
from hecos.core.system.module_scanner import update_capability_registry
update_capability_registry(cfg.config, debug_log=False)

from hecos.core.system.module_state import get_plugin_module
from hecos.core.ipc.proxy import PluginProxy

proxy_obj = get_plugin_module('IMAGE_GEN')

if proxy_obj is None:
    print('FAIL: Plugin not found')
elif isinstance(proxy_obj, PluginProxy):
    print('SUCCESS: IMAGE_GEN loaded as PluginProxy (subprocess isolation active!)')
    print('  Alive:', proxy_obj.is_alive())
    print('  PID:', proxy_obj._process.pid if proxy_obj._process else 'N/A')
    # Verify tools interface
    result = proxy_obj.tools.generate_image(prompt='A mountain landscape at sunset')
    print('  Call result (first 80 chars):', str(result)[:80])
else:
    print('INFO: IMAGE_GEN loaded as regular module (lazy-load fallback)')
    print('  Type:', type(proxy_obj))
