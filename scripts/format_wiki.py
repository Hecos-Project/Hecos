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
    files = [f for f in os.listdir(WIKI_DIR) if f.endswith(".md") and not f.startswith("_")]
    
    # Map: base_name -> {lang -> {filename, title}}
    structure = {}
    
    for filename in files:
        # Expected format: XX_name_lang.md
        parts = filename.replace(".md", "").split("_")
        if len(parts) < 3:
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
            # Remove existing switcher if present (simple check for "---")
            if content.startswith("[[ 🇬🇧") or "Languages" in content[:50]:
                # This is a bit risky, let's just prepend if not already there
                pass
            
            # Simple injection: replace first line if it's already a switcher, or prepend
            if " | " in content.split("\n")[0] and "[[" in content.split("\n")[0]:
                lines = content.split("\n")
                # Skip the first few lines if they look like a header
                new_content = switcher_line + "\n".join(lines[2:]) # Skip old switcher + separator
            else:
                new_content = switcher_line + content
                
            with open(info["path"], "w", encoding="utf-8") as f:
                f.write(new_content)

    # 2. Generate _Sidebar.md
    sidebar_content = "### 🌐 Languages\n"
    sidebar_content += "* [[ 🇬🇧 English | 00_introduction_en ]]\n"
    sidebar_content += "* [[ 🇮🇹 Italiano | 00_introduction_it ]]\n"
    sidebar_content += "* [[ 🇪🇸 Español | 00_introduction_es ]]\n\n"
    
    for lang_code, lang_info in LANGUAGES.items():
        sidebar_content += f"### {lang_info['label']}\n"
        
        # Sort pages by prefix
        sorted_pages = sorted(structure.items(), key=lambda x: x[0])
        for base_name, langs in sorted_pages:
            if lang_code in langs:
                page_info = langs[lang_code]
                sidebar_content += f"* [[ {page_info['title']} | {page_info['filename']} ]]\n"
        sidebar_content += "\n"
        
    sidebar_path = os.path.join(WIKI_DIR, "_Sidebar.md")
    with open(sidebar_path, "w", encoding="utf-8") as f:
        f.write(sidebar_content)
        
    print(f"Processed {len(files)} files. Generated _Sidebar.md")

if __name__ == "__main__":
    process_wiki()
