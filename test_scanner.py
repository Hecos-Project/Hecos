import sys
sys.path.insert(0, r'C:\Hecos')

from hecos.core.system.module_scanner import update_capability_registry

config = {'plugins': {}}
skills = update_capability_registry(config, debug_log=True)

print()
print('=== Moduli caricati ===')
import json
print(json.dumps(skills, indent=2, default=str, ensure_ascii=False))
