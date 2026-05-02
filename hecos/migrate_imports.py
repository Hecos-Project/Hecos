import os

replacements = {
    'module_loader': 'module_loader',
    'module_scanner': 'module_scanner',
    'module_state': 'module_state',
    'module_docs': 'module_docs',
    'module_config_sync': 'module_config_sync'
}

count = 0
for root, dirs, files in os.walk(r'c:\Hecos-Core\hecos'):
    if '__pycache__' in root or '.git' in root or 'node_modules' in root:
        continue
    for file in files:
        if file.endswith('.py') or file.endswith('.js') or file.endswith('.html'):
            path = os.path.join(root, file)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                modified = False
                for old, new in replacements.items():
                    if old in content:
                        content = content.replace(old, new)
                        modified = True
                if modified:
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    print(f'Updated: {path}')
                    count += 1
            except Exception as e:
                pass

print(f"Total files updated: {count}")
