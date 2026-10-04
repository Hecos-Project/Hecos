"""
format_wiki.py
Adds or refreshes language switcher banners in all Hecos Wiki pages.

Usage (standalone or called by Publish-Wiki.ps1):
    python scripts/format_wiki.py
    python scripts/format_wiki.py --wiki-path "D:\\other\\Hecos-Wiki"
"""

import os
import re
import argparse

DEFAULT_WIKI_DIR = r"C:\Hecos-Wiki"

LANGUAGES = {
    "en": {"label": "🇬🇧 English", "flag": "🇬🇧"},
    "it": {"label": "🇮🇹 Italiano", "flag": "🇮🇹"},
    "es": {"label": "🇪🇸 Español", "flag": "🇪🇸"}
}

def get_h1(content):
    match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    return match.group(1).strip() if match else None

def process_wiki(wiki_dir):
    if not os.path.exists(wiki_dir):
        print(f"[ERROR] Wiki directory not found: {wiki_dir}")
        return

    files = [f for f in os.listdir(wiki_dir) if f.endswith(".md") and not f.startswith("_")]

    # Map: base_name -> {lang -> {filename, title, path, content}}
    structure = {}
    for filename in files:
        parts = filename.replace(".md", "").split("_")
        if len(parts) < 2:
            continue
        lang = parts[-1]
        base_name = "_".join(parts[:-1])
        if lang not in LANGUAGES:
            continue
        path = os.path.join(wiki_dir, filename)
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

    updated = 0
    for base_name, langs in structure.items():
        available_langs = sorted(langs.keys(), key=lambda l: list(LANGUAGES.keys()).index(l))
        switcher_links = []
        for l in available_langs:
            label = LANGUAGES[l]["flag"] + " " + LANGUAGES[l]["label"].split(" ")[1]
            target = langs[l]["filename"]
            switcher_links.append(f"[[ {label} | {target} ]]")
        switcher_line = " | ".join(switcher_links) + "\n\n---\n"

        for lang_code, info in langs.items():
            content = info["content"]
            first_line = content.split("\n")[0]
            if " | " in first_line and "[[" in first_line:
                lines = content.split("\n")
                new_content = switcher_line + "\n".join(lines[2:])
            else:
                new_content = switcher_line + "\n" + content
            with open(info["path"], "w", encoding="utf-8") as f:
                f.write(new_content)
            updated += 1

    print(f"[OK] Processed {len(files)} files, updated {updated} with language switchers.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Format Hecos Wiki: inject language switchers.")
    parser.add_argument("--wiki-path", default=DEFAULT_WIKI_DIR, help="Path to the local Hecos-Wiki repo")
    args = parser.parse_args()
    process_wiki(args.wiki_path)
