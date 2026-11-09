import sys
sys.path.insert(0, '.')
from hecos.core.system.module_scanner import update_capability_registry
from hecos.core.system.module_docs import get_tools_schema

update_capability_registry()
tools = get_tools_schema()
has_func = sum(1 for t in tools if 'function' in t)
no_func = sum(1 for t in tools if 'function' not in t)
igen = [t for t in tools if 'IMAGE_GEN' in t.get('function', {}).get('name', '')]
print(f"Total tools: {len(tools)} | With function: {has_func} | Without: {no_func}")
print(f"IMAGE_GEN tools: {[t['function']['name'] for t in igen]}")

