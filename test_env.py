import os
import sys

print("--- ENVIRONMENT TEST ---", flush=True)
print(f"CWD: {os.getcwd()}")
print(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'NOT SET')}")
print(f"SYS.PATH: {sys.path}")

try:
    import zentra
    print("[+] import zentra: SUCCESS")
except Exception as e:
    print(f"[-] import zentra: FAILED ({e})")

try:
    # Adding zentra specifically to test if core/app are reachable
    root = os.path.abspath(os.path.dirname(__file__))
    zpath = os.path.join(root, "zentra")
    if zpath not in sys.path:
        sys.path.insert(0, zpath)
    
    import core
    print("[+] import core: SUCCESS")
    import app
    print("[+] import app: SUCCESS")
    import plugins
    print("[+] import plugins: SUCCESS")
except Exception as e:
    print(f"[-] import subpackages: FAILED ({e})")

print("--- END TEST ---")
