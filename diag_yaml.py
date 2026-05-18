import os

path = r'c:\Hecos\hecos\config\data\system.yaml'
with open(path, 'rb') as f:
    data = f.read()

print(f"File size in bytes: {len(data)}")
print(f"Last 100 bytes (hex): {data[-100:].hex()}")
print(f"Last 100 bytes (ascii): {data[-100:].decode('utf-8', errors='replace')}")

# Match duplicate keys
content = data.decode('utf-8', errors='replace')
count = content.count('action_console_enabled')
print(f"Occurrences of 'action_console_enabled': {count}")
