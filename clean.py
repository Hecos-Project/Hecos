import glob

for file in glob.glob('c:/Hecos/README*.md'):
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    content = content.replace('[cite: 1]', '')
    
    with open(file, 'w', encoding='utf-8') as f:
        f.write(content)
