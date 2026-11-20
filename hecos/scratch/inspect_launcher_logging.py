with open('hecos/hpm/image_gen/plugin/local/launcher.py', 'r', encoding='utf-8') as f:
    lines = f.read().splitlines()

for i, l in enumerate(lines):
    if 'print(' in l or 'logger.' in l:
        safe = l.encode('ascii', 'replace').decode('ascii')
        print(f"Line {i+1}: {safe}")

