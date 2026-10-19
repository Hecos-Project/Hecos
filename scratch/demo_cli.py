"""
scratch/demo_cli.py
Demonstration script for Hecos Unified Progress System in CLI.
Run:
    python scratch/demo_cli.py
"""
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hecos.core.progress import progress


def main():
    print("\n" + "=" * 60)
    print("  HECOS UNIFIED PROGRESS SYSTEM - CLI DEMO")
    print("=" * 60 + "\n")

    phases = [
        ("download", 40.0, "Download Pacchetto"),
        ("deps", 40.0, "Installazione Pip"),
        ("verify", 20.0, "Verifica e Setup"),
    ]

    total_bytes = 35 * 1024 * 1024  # 35 MB
    chunk_size = 2 * 1024 * 1024   # 2 MB per step

    with progress.task("cli_demo", "Installazione Kokoro Model", source="DEMO", phases=phases) as t:
        # Phase 1: Download
        t.phase("download", message="Scaricamento pesi neurali...")
        done = 0
        while done < total_bytes:
            time.sleep(0.18)
            done = min(total_bytes, done + chunk_size)
            t.advance(bytes_done=done, total_bytes=total_bytes)

        # Phase 2: Pip installation simulation
        t.phase("deps", message="Installazione pacchetti pip...")
        pip_samples = [
            "Collecting kokoro>=0.8.0",
            "Downloading kokoro-0.8.0-py3-none-any.whl (1.2 MB)",
            "Collecting misaki[en]>=0.4.0",
            "Installing collected packages: misaki, kokoro",
            "Successfully installed kokoro-0.8.0 misaki-0.4.0"
        ]
        for line in pip_samples:
            time.sleep(0.4)
            t.advance(message=line[:50], log=line)

        # Phase 3: Finalize
        t.phase("verify", message="Verifica hash e registrazione...")
        time.sleep(0.6)
        t.done("Installazione completata con successo al 100%!")

    print("\n[OK] Dimostrazione CLI completata con successo.\n")


if __name__ == "__main__":
    main()
