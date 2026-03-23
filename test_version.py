import sys
import os
sys.path.append(os.getcwd())

from core.system.version import VERSION, get_version_string

print(f"DEBUG: VERSION type: {type(VERSION)}")
print(f"DEBUG: VERSION value: '{VERSION}'")
print(f"DEBUG: version string: {get_version_string()}")
