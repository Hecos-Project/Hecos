import os

docs_dir = r"c:\Zentra-Core\docs"
user_dir = os.path.join(docs_dir, "user")
tech_dir = os.path.join(docs_dir, "tech")

# Mapping for User Guide
user_map = {
    "introduzione": "introduction",
    "avvio": "boot",
    "interfaccia": "ui",
    "configurazione": "config",
    "plugin": "plugins",
    "visione": "vision",
    "risposte": "responses",
    "immagini": "images",
    "webui": "webui",
    "sicurezza": "security",
    "mobile": "mobile",
    "troubleshooting": "troubleshooting",
    "agente": "agent",
    "keymanager": "keymanager",
    "routing": "routing"
}

# Mapping for Tech Guide
tech_map = {
    "architettura": "architecture",
    "data_flow": "data_flow",
    "moduli": "modules",
    "infrastruttura": "infrastructure",
    "best_practices": "best_practices"
}

def clean_dir(target_dir, mapping):
    print(f"Cleaning {target_dir}...")
    files = os.listdir(target_dir)
    for f in files:
        if not f.endswith(".md"): continue
        path = os.path.join(target_dir, f)
        
        # 1. Identify legacy names and rename to English + suffix
        # Pattern: XX_basename.md or XX_basename_lang.md
        parts = f.replace(".md", "").split("_")
        if len(parts) < 2: continue
        
        prefix = parts[0] # e.g. "01"
        base = parts[1]   # e.g. "avvio" or "boot"
        lang = "en"       # default if no suffix
        if len(parts) > 2:
            lang = parts[2]
            
        # Re-map base if it's in Italian
        new_base = mapping.get(base, base)
        new_name = f"{prefix}_{new_base}_{lang}.md"
        new_path = os.path.join(target_dir, new_name)
        
        if f != new_name:
            if os.path.exists(new_path):
                print(f"  Removing duplicate/legacy: {f}")
                os.remove(path)
            else:
                print(f"  Renaming: {f} -> {new_name}")
                os.rename(path, new_path)
        else:
            print(f"  OK: {f}")

clean_dir(user_dir, user_map)
clean_dir(tech_dir, tech_map)

# Final check: Ensure 08_webui_en.md exists (fallback)
webui_en = os.path.join(user_dir, "08_webui_en.md")
if not os.path.exists(webui_en):
    with open(webui_en, "w", encoding="utf-8") as f:
        f.write("# 💻 Native WebUI\n\nZentra's WebUI is the modern graphical interface.")

print("Done.")
