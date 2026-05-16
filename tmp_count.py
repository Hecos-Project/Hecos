import os

folder = r"c:\Hecos\hecos\modules\web_ui"
results = []

for root, _, files in os.walk(folder):
    for f in files:
        if f.endswith(('.js', '.html', '.css', '.py')):
            path = os.path.join(root, f)
            try:
                with open(path, 'r', encoding='utf-8') as file:
                    lines = sum(1 for _ in file)
                rel_path = os.path.relpath(path, folder)
                results.append((lines, rel_path))
            except Exception as e:
                pass

results.sort(reverse=True)
with open(r"c:\Hecos\tmp_results.txt", "w", encoding="utf-8") as out:
    out.write("Files by line count (Top 40):\n")
    out.write("-" * 50 + "\n")
    for lines, path in results[:40]:
        out.write(f"{lines:5} lines : {path}\n")
