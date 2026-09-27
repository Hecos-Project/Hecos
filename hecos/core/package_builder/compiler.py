import sys
import subprocess
from pathlib import Path
from hecos.core.package_builder.logger import info, error

def compile_package(src_dir: str, out_dir: str = None, builder_path: str = None) -> dict:
    info(f"Starting compilation for {src_dir}")
    builder_path_str = builder_path if builder_path else r"C:\Hecos-Packages\Hecos_HPM_Builder" 
    try:
        out_dir_str = f"r'{out_dir}'" if out_dir else "None"
        code = f'''
import sys
sys.path.insert(0, r"{builder_path_str}")
from modules.builder import _build_single_package
from pathlib import Path

target = Path(r"{src_dir}")
out = {out_dir_str}
if not out:
    from modules.settings import get_packages_dir
    out = get_packages_dir()
out = Path(out)

try:
    from modules.settings import get_src_dir
    src_root_name = get_src_dir().name
except:
    src_root_name = "sources"

cat = target.parent.name
if cat != src_root_name:
    final_out = out / cat
else:
    final_out = out
print("FINAL_OUT_DIR=" + str(final_out))

success = _build_single_package(target, out)
if not success:
    sys.exit(1)
'''
        result = subprocess.run([sys.executable, "-c", code], check=True, capture_output=True, text=True)
        info("Compilation finished successfully.")
        
        final_out_dir = out_dir
        for line in result.stdout.splitlines():
            if line.startswith("FINAL_OUT_DIR="):
                final_out_dir = line.split("=", 1)[1]
                
        if result.stdout:
            info(f"Builder STDOUT: {result.stdout}")
            
        return {"ok": True, "out_dir": final_out_dir, "logs": result.stdout}
    except subprocess.CalledProcessError as e:
        error(f"Error compiling package (Subprocess failed):\nSTDOUT: {e.stdout}\nSTDERR: {e.stderr}")
        return {"ok": False, "error": "Build failed (check logs).", "logs": e.stdout + "\n" + e.stderr}
    except Exception as e:
        error(f"Error compiling package: {e}")
        return {"ok": False, "error": str(e), "logs": ""}
