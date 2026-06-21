import subprocess
import os

script_path = r"C:\Hecos\scripts\windows\run\HECOS_TRAY_WIN.bat"
CWD = r"C:\Hecos"

print("Test 2")
try:
    subprocess.Popen(["cmd", "/c", "start", "", script_path], cwd=CWD)
except Exception as e:
    print(e)
