with open('hecos/hpm/image_gen/plugin/generator.py', 'r', encoding='utf-8') as f:
    lines = f.read().splitlines()

for i, l in enumerate(lines):
    if '\u2192' in l:
        safe_line = l.replace('\u2192', '->')
        print(f"Line {i+1}: {safe_line}")

