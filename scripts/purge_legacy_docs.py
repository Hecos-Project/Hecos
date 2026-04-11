import os

docs_dir = r"c:\Zentra-Core\docs"
user_dir = os.path.join(docs_dir, "user")
tech_dir = os.path.join(docs_dir, "tech")

# Valid base names in English
user_bases = ["introduction", "boot", "ui", "config", "plugins", "vision", "responses", "images", "webui", "security", "mobile", "troubleshooting", "agent", "keymanager", "routing"]
tech_bases = ["architecture", "data_flow", "modules", "infrastructure", "best_practices"]
langs = ["en", "it", "es"]

def purge_legacy(target_dir, valid_bases):
    print(f"Purging {target_dir}...")
    files = os.listdir(target_dir)
    for f in files:
        if not f.endswith(".md"): continue
        path = os.path.join(target_dir, f)
        
        # Check if it follows the new convention: XX_englishname_lang.md
        parts = f.replace(".md", "").split("_")
        is_legacy = True
        
        if len(parts) == 3:
            prefix, base, lang = parts
            if prefix.isdigit() and base in valid_bases and lang in langs:
                is_legacy = False
        
        if is_legacy:
            print(f"  Removing legacy file: {f}")
            try:
                os.remove(path)
            except Exception as e:
                print(f"  FAILED to remove {f}: {e}")

purge_legacy(user_dir, user_bases)
purge_legacy(tech_dir, tech_bases)

print("Done.")
