import os
import glob
import re
try:
    import tomllib
except ImportError:
    import tomli as tomllib

packages_dir = r"C:\Hecos-Packages"
exclude = ["image_gen_src"]

for pkg_src in glob.glob(os.path.join(packages_dir, "*_src")):
    pkg_name = os.path.basename(pkg_src)
    if pkg_name in exclude:
        continue
    
    print(f"Migrating {pkg_name}...")
    
    # 1. Update TOML & fix broken pip_requirements
    toml_path = os.path.join(pkg_src, "hpkg_manifest.toml")
    if os.path.exists(toml_path):
        with open(toml_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Fix broken multiline pip_requirements
        # If we see pip_requirements = ["something"] followed by random strings and ]
        # we can just regex replace it
        content = re.sub(r'(pip_requirements\s*=\s*\[[^\]]*\])[^\[\]]*\]', r'\1', content)
        
        # Add pip_isolation = "isolated" if not present
        if "pip_isolation" not in content:
            # Just append it after pip_requirements, or before tag
            content = re.sub(r'(type\s*=\s*".*?"\n)', r'\1pip_isolation = "isolated"\n', content)
            
        with open(toml_path, "w", encoding="utf-8") as f:
            f.write(content)
        print("  - Updated hpkg_manifest.toml")
        
        # Verify it parses
        try:
            with open(toml_path, "rb") as f:
                tomllib.load(f)
        except Exception as e:
            print(f"  - ERROR parsing TOML: {e}")
            
    # 2. Delete runner.py
    for root, dirs, files in os.walk(os.path.join(pkg_src, "plugin")):
        if "runner.py" in files:
            runner_path = os.path.join(root, "runner.py")
            os.remove(runner_path)
            print(f"  - Deleted {os.path.relpath(runner_path, pkg_src)}")
            
    # 3. Update imports in python files
    for root, dirs, files in os.walk(os.path.join(pkg_src, "plugin")):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                with open(file_path, "r", encoding="utf-8") as f:
                    file_content = f.read()
                
                new_content = file_content.replace("from hecos.core.logging import logger", "from hecos_sdk import logger")
                if new_content != file_content:
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(new_content)
                    print(f"  - Updated imports in {os.path.relpath(file_path, pkg_src)}")
                    
    print(f"  -> Done.")

