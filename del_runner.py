import os

filepath = r"C:\Hecos-Packages\Hecos_HPM_Builder\modules\scaffold.py"
with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Remove lines 106 to 200 (indices 105 to 199)
del lines[105:200]

with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(lines)
