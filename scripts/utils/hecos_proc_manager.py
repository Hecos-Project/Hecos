import os
import sys
import psutil
import time

def get_hecos_processes():
    """Finds all python and piper processes."""
    hecos_procs = []
    my_pid = os.getpid()
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            pid = proc.info['pid']
            if pid == my_pid:
                continue
                
            name = proc.info.get('name', '').lower()
            cmdline = proc.info.get('cmdline') or []
            cmd_str = " ".join(cmdline).lower()
            
            p_type = None
            
            # Ignore Antigravity IDE
            if "pyrefly" in name:
                continue

            # Python, Piper, or renamed Hecos executables (hecos_module_*.exe, hecos_core.exe)
            if not ("python" in name or "piper" in name or "hecos" in name):
                continue
                
            if "piper" in name:
                p_type = "Piper TTS"
            elif "monitor.py" in cmd_str:
                if "web_ui" in cmd_str or "hecos_web" in cmd_str:
                    p_type = "Web Monitor"
                else:
                    p_type = "Console Monitor"
            elif "hecos.app.main" in cmd_str or "hecos_core" in name or "main.py" in cmd_str:
                p_type = "Hecos Core"
            elif "web_ui.server" in cmd_str or "hecos_web" in name:
                p_type = "Web Server"
            elif "tray" in cmd_str or "hecos_tray" in name:
                p_type = "Hecos Tray"
            elif "hecos_sdk.runner" in cmd_str or "hecos_module_" in name:
                # Extract module name if possible
                mod_name = name.replace("hecos_module_", "").replace(".exe", "").upper()
                p_type = f"HPM Subprocess ({mod_name})" if "hecos_module_" in name else "HPM Subprocess"
            elif "python" in name or "hecos" in name:
                # If we got here but it's a hecos executable or python running something hecos-related
                if "hecos" in name or "hecos" in cmd_str:
                    p_type = "Hecos (Generic)"
                else:
                    continue # Skip unrelated python processes

            if p_type:
                hecos_procs.append({
                    "pid": proc.info['pid'],
                    "type": p_type,
                    "cmd": " ".join(cmdline) or name
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return hecos_procs

def main():
    print("\n" + "="*60)
    print("   HECOS PROCESS MANAGER")
    print("="*60)
    
    procs = get_hecos_processes()
    
    if not procs:
        print("\n[!] Nessun processo Hecos rilevato.")
        input("\nPremi INVIO per uscire...")
        return

    # Count duplicates based on exact command line
    counts = {}
    for p in procs:
        counts[p['cmd']] = counts.get(p['cmd'], 0) + 1
    
    print(f"\nProcessi trovati ({len(procs)}):")
    print(f"{'PID':<8} | {'Tipo':<25} | {'Comando'}")
    print("-" * 80)
    
    has_duplicates = False
    for p in procs:
        warn = ""
        if counts[p['cmd']] > 1:
            warn = " [!!! DUPLICATO !!!]"
            has_duplicates = True
        
        # Truncate cmd for display if too long
        display_cmd = p['cmd']
        if len(display_cmd) > 50:
            display_cmd = display_cmd[:47] + "..."
            
        print(f"{p['pid']:<8} | {p['type']:<25} | {display_cmd}{warn}")

    if has_duplicates:
        print("\n" + "!"*80)
        print(" ATTENZIONE: Sono state rilevate istanze duplicate (stesso comando)!")
        print(" Questo potrebbe causare conflitti di memoria o dati vecchi.")
        print("!"*80)

    print("\nCosa vuoi fare?")
    print("1) Chiudi TUTTI i processi Hecos")
    print("2) Chiudi solo i DUPLICATI")
    print("3) Chiudi un processo specifico (inserisci PID)")
    print("q) Esci senza fare nulla")
    
    choice = input("\nScelta > ").lower()
    
    if choice == '1':
        for p in procs:
            try:
                psutil.Process(p['pid']).kill()  # Force kill instead of gentle terminate
                print(f"Ucciso PID {p['pid']} ({p['type']})")
            except: pass
        print("\nPulizia completata.")
    
    elif choice == '2':
        for p in procs:
            if counts[p['cmd']] > 1:
                try:
                    psutil.Process(p['pid']).kill()
                    print(f"Ucciso duplicato PID {p['pid']} ({p['type']})")
                    counts[p['cmd']] -= 1 # Keep at least one
                except: pass
    
    elif choice.isdigit():
        pid_to_kill = int(choice)
        try:
            psutil.Process(pid_to_kill).kill()
            print(f"Ucciso PID {pid_to_kill}")
        except Exception as e:
            print(f"Errore nel terminare il processo: {e}")
            
    elif choice == 'q':
        return
    else:
        print("Scelta non valida.")

    input("\nOperazione completata. Premi INVIO per uscire...")

if __name__ == "__main__":
    main()
