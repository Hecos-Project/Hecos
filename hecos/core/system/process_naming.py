import sys
import os
import shutil

def get_named_executable(name: str, base_exe: str = None) -> str:
    """
    Returns a path to a Python executable that has the given name.
    Useful on Windows to show custom process names in Task Manager.
    If it cannot create the named executable, it falls back to the original executable.
    """
    if base_exe is None:
        base_exe = sys.executable

    if not name.lower().endswith(".exe"):
        name += ".exe"
        
    base_dir = os.path.dirname(base_exe)
    target_path = os.path.join(base_dir, name)
    
    if os.path.exists(target_path):
        return target_path
        
    try:
        shutil.copy2(base_exe, target_path)
        return target_path
    except Exception:
        return base_exe
