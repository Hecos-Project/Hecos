#!/usr/bin/env python
# Proxy root per Zentra Main
import sys
import os

# --- CRITICAL SYS.PATH FIX ---
root_path = os.path.abspath(os.path.dirname(__file__))
zentra_path = os.path.join(root_path, "zentra")

sys.path.insert(0, root_path)
sys.path.insert(0, zentra_path)
# -----------------------------

if __name__ == "__main__":
    try:
        # Tenta il caricamento via package (v0.14+)
        from zentra.main import main
        main()
    except ImportError:
        try:
            # Fallback legacy (se zentra/ è nel path, questo carica zentra/main.py)
            import main as zmain
            zmain.main()
        except Exception as e:
            print(f"[MAIN PROXY] Fallimento totale: {e}")
            sys.exit(1)