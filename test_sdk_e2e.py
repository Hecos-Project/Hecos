import sys
sys.path.insert(0, r'C:\Hecos')

from hecos.core.ipc.proxy import ModuleProxy
import time

venv_python = r'C:\Hecos\hecos\hpm\image_gen\venv\Scripts\python.exe'
module_dir   = r'C:\Hecos\hecos\hpm\image_gen'

proxy = ModuleProxy('IMAGE_GEN', module_dir, venv_python)
ok = proxy.start()
print('start ok:', ok)

time.sleep(2)
print('alive:', proxy.is_alive())

# Test info call
print('--- Info request ---')
info = proxy.get_manifest()
print('manifest:', info)

proxy.stop()
print('stopped cleanly.')
