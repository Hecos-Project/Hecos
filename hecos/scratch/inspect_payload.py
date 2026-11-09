import json
import sys

with open('hecos/logs/payloads.log', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

idx = text.rfind('2026-11-09T06:23:59')
start_idx = text.rfind('=== PAYLOAD START', 0, idx)
json_start = text.find('{', start_idx)
json_end = text.rfind('}', start_idx, text.find('=== PAYLOAD END', start_idx)) + 1

data = json.loads(text[json_start:json_end])
print('Model:', data.get('model'))
messages = data.get('messages', [])
print('Number of messages:', len(messages))
for i, m in enumerate(messages):
    print(f"Msg {i} role: {m.get('role')}, len: {len(m.get('content', ''))}")

sys_content = messages[0]['content']
print('\n--- System content preview ---')
lines = sys_content.split('\n')
print(f'Total lines: {len(lines)}, total chars: {len(sys_content)}')
for i, l in enumerate(lines):
    if l.startswith('###') or l.startswith('[') or 'CAPABILITIES' in l or 'PROTOCOL' in l:
        print(f"Line {i:4d}: {l[:100]}")

