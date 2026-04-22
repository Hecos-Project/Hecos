import sys
import os
sys.path.append(r"C:\Zentra-Core")

from zentra.core.audio import ptt_bus
import time

print("Starting PTT Bus test...")
ptt_bus.start()

print("Status:", ptt_bus.get_status())

print("Testing is_pressed directly...")
try:
    import keyboard
    print("keyboard mod loaded.")
except Exception as e:
    print("err:", e)

for i in range(50):
    if ptt_bus.is_ptt_active():
        print(f"[{i}] PTT IS ACTIVE! Source:", ptt_bus.get_last_source())
    time.sleep(0.1)

print("Test finished.")
