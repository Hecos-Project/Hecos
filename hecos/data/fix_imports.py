import os

packages = ['calendar', 'reminder', 'lists']
hpm_dir = r'C:\Hecos\hecos\hpm'

count = 0
for pkg in packages:
    pkg_dir = os.path.join(hpm_dir, pkg)
    for root, dirs, files in os.walk(pkg_dir):
        for file in files:
            if not file.endswith('.py'):
                continue
            path = os.path.join(root, file)
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if 'hecos.plugins' in content:
                new_content = content.replace('hecos.plugins', 'hecos.hpm')
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"Patched {path}")
                count += 1
print(f"Patched {count} files total.")
