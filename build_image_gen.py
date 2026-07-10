import sys
sys.path.insert(0, r"C:\Hecos-Packages\Hecos_HPM_Builder")
from modules.builder import _build_single_package
from pathlib import Path
_build_single_package(Path(r"C:\Hecos-Packages\image_gen_src"), Path(r"C:\Hecos-Packages\Hecos_HPM_Builder\out"))
