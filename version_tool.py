#!/usr/bin/env python
"""
Utility per visualizzare le informazioni di versione.
Esegui: python version_tool.py
"""

from core.version import get_full_info, get_version_string

if __name__ == "__main__":
    info = get_full_info()
    print("=" * 50)
    print(get_version_string())
    print("=" * 50)
    for key, value in info.items():
        if key != "build":
            print(f"{key.replace('_', ' ').title()}: {value}")
    print("\nBuild Info:")
    for k, v in info["build"].items():
        print(f"  {k.replace('_', ' ').title()}: {v}")