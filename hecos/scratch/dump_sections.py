import json
import sys

with open('hecos/logs/payloads.log', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

idx = text.rfind('2026-11-09T06:23:59')
start_idx = text.rfind('=== PAYLOAD START', 0, idx)
json_start = text.find('{', start_idx)
json_end = text.rfind('}', start_idx, text.find('=== PAYLOAD END', start_idx)) + 1
data = json.loads(text[json_start:json_end])
lines = data['messages'][0]['content'].split('\n')

with open('hecos/scratch/system_prompt_sections.txt', 'w', encoding='utf-8') as out:
    for i, line in enumerate(lines):
        if not line.startswith('  - ') and not line.startswith('    '):
            out.write(f"L{i:4d}: {line[:120]}\n")

print(f"Dumped non-indented lines. Total lines: {len(lines)}")

