import os
import shutil
import time

src = r"c:\Zentra-Core\zentra\plugins"
dst = r"c:\Zentra-Core\zentra\modules"
dirs = ["web_ui", "memory", "models", "executor", "mcp_bridge", "dashboard", "sys_net", "help"]

# 1. Create __init__.py if not exists
if not os.path.exists(dst):
    os.makedirs(dst)
with open(os.path.join(dst, "__init__.py"), "w") as f:
    f.write("# Core Modules initialization\n")

# 2. Move the folders
moved = 0
for d in dirs:
    src_path = os.path.join(src, d)
    dst_path = os.path.join(dst, d)
    if os.path.exists(src_path) and not os.path.exists(dst_path):
        shutil.move(src_path, dst_path)
        print(f"Moved {d} to modules/")
        moved += 1
    elif os.path.exists(dst_path):
        print(f"Already moved: {d}")

print(f"\nDone! Physically moved {moved} folders.")
