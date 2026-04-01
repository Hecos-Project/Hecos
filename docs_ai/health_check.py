import json
import os
import glob

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    capabilities_dir = os.path.join(script_dir, "capabilities")
    
    missing = []
    
    with open("health_check_result.txt", "w", encoding="utf-8") as out:
        for json_file in glob.glob(os.path.join(capabilities_dir, "*.json")):
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            capabilities = data.get("capabilities", [])
            for cap in capabilities:
                cap_id = cap.get("id", "UNKNOWN")
                impl = cap.get("implementation", {})
                core_files = impl.get("core_files", [])
                
                for file_path in core_files:
                    root_path = os.path.abspath(os.path.join(script_dir, ".."))
                    full_path = os.path.join(root_path, file_path)
                    
                    if not os.path.exists(full_path):
                        missing.append(f"{cap_id}: {file_path} MISSING")
                        out.write(f"MISSING: {file_path} (from {cap_id})\n")
                    else:
                        out.write(f"OK: {file_path}\n")
                        
        if not missing:
            out.write("RESULTS: ALL OK\n")
        else:
            out.write(f"RESULTS: {len(missing)} MISSING FILES\n")

if __name__ == "__main__":
    main()
