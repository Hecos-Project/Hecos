import os
import re

WIKI_DIR = r"C:\Hecos-Wiki"

LANGUAGES = {
    "en": {"label": "🇬🇧 English", "flag": "🇬🇧"},
    "it": {"label": "🇮🇹 Italiano", "flag": "🇮🇹"},
    "es": {"label": "🇪🇸 Español", "flag": "🇪🇸"}
}

def get_h1(content):
    match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return None

def process_wiki():
    if not os.path.exists(WIKI_DIR):
        print(f"Wiki directory not found: {WIKI_DIR}")
        return

    files = [f for f in os.listdir(WIKI_DIR) if f.endswith(".md") and not f.startswith("_")]
    
    # Map: base_name -> {lang -> {filename, title}}
    structure = {}
    
    for filename in files:
        parts = filename.replace(".md", "").split("_")
        if len(parts) < 2:
            continue
            
        lang = parts[-1]
        base_name = "_".join(parts[:-1])
        
        if lang not in LANGUAGES:
            continue
            
        path = os.path.join(WIKI_DIR, filename)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            
        title = get_h1(content) or filename
        
        if base_name not in structure:
            structure[base_name] = {}
        
        structure[base_name][lang] = {
            "filename": filename.replace(".md", ""),
            "title": title,
            "path": path,
            "content": content
        }

    # 1. Update each file with a language switcher
    for base_name, langs in structure.items():
        # Sort langs to ensure consistent order: en, it, es
        available_langs = sorted(langs.keys(), key=lambda l: list(LANGUAGES.keys()).index(l))
        
        switcher_links = []
        for l in available_langs:
            label = LANGUAGES[l]["flag"] + " " + LANGUAGES[l]["label"].split(" ")[1]
            target = langs[l]["filename"]
            switcher_links.append(f"[[ {label} | {target} ]]")
        
        switcher_line = " | ".join(switcher_links) + "\n\n---\n"
        
        for lang_code, info in langs.items():
            content = info["content"]
            
            # Simple injection: replace first line if it's already a switcher, or prepend
            first_line = content.split("\n")[0]
            if " | " in first_line and "[[" in first_line:
                lines = content.split("\n")
                new_content = switcher_line + "\n".join(lines[2:]) # Skip old switcher + separator
            else:
                new_content = switcher_line + "\n" + content
                
            with open(info["path"], "w", encoding="utf-8") as f:
                f.write(new_content)

    print(f"Processed {len(files)} files and injected language switchers.")

if __name__ == "__main__":
    process_wiki()
