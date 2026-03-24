import os
import re

def get_current_version():
    with open("core/version", "r") as f:
        return f.read().strip()

def update_readme(file_path, version):
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Pattern per trovare "Version X.Y.Z" o "Versione X.Y.Z" o "Versión X.Y.Z"
    # Cerchiamo di essere specifici per evitare sostituzioni errate
    new_content = re.sub(
        r"(Version|Versione|Versión)\s+\d+\.\d+\.\d+",
        f"\\1 {version}",
        content
    )

    if content != new_content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"✅ Updated {file_path} to {version}")
    else:
        print(f"ℹ️ {file_path} is already up to date or version pattern not found.")

if __name__ == "__main__":
    version = get_current_version()
    readmes = ["README.md", "README_ITA.md", "README_ESP.md"]
    
    print(f"Syncing version {version} to README files...")
    for readme in readmes:
        update_readme(readme, version)
