import os

# Root directory for Hecos files
root_dir = r"c:\Hecos\hecos"

# Replacements for branding cleanup and accessibility
replacements = {
    "Hecos_Core_Logo": "Hecos_Logo",
    "Agentic Layer & Orchestrator": "Helping Companion System",
    "Agentic Layer": "Helping Companion System",
}

files_modified = 0

for root, _, files in os.walk(root_dir):
    for file in files:
        if file.endswith((".py", ".html", ".js", ".css", ".yaml", ".json")):
            file_path = os.path.join(root, file)
            try:
                # Use binary check or skip non-text if needed, but these extensions are safe
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                new_content = content
                modified = False
                for old, new in replacements.items():
                    if old in new_content:
                        new_content = new_content.replace(old, new)
                        modified = True
                
                if modified:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    print(f"Fixed branding in: {file_path}")
                    files_modified += 1
            except Exception as e:
                print(f"Error processing {file_path}: {e}")

print(f"Completed! Total files modified: {files_modified}")
