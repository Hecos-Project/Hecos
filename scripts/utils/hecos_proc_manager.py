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
            
            # Solo Python o Piper
            if not ("python" in name or "piper" in name):
                continue
                
            if "piper" in name:
                p_type = "Piper TTS"
            elif "monitor.py" in cmd_str:
                if "web_ui" in cmd_str or "hecos_web" in cmd_str:
                    p_type = "Web Monitor"
                else:
                    p_type = "Console Monitor"
            elif "hecos.app.main" in cmd_str or "main.py" in cmd_str:
                p_type = "Hecos Core"
            elif "web_ui.server" in cmd_str:
                p_type = "Web Server"
            elif "tray" in cmd_str:
                p_type = "Hecos Tray"
            elif "hecos_sdk.runner" in cmd_str:
                p_type = "HPM Subprocess"
            elif "python" in name:
                p_type = "Python (Generic)"

            if p_type:
                hecos_procs.append({
                    "pid": proc.info['pid'],
                    "type": p_type,
                    "cmd": " ".join(cmdline)
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
    print(f"{'PID':<8} | {'Tipo':<18} | {'Comando'}")
    print("-" * 80)
    
    has_duplicates = False
    for p in procs:
        warn = ""
        if counts[p['cmd']] > 1:
            warn = " [!!! DUPLICATO !!!]"
            has_duplicates = True
        
        # Truncate cmd for display if too long
        display_cmd = p['cmd']
        if len(display_cmd) > 60:
            display_cmd = display_cmd[:57] + "..."
            
        print(f"{p['pid']:<8} | {p['type']:<18} | {display_cmd}{warn}")

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
                psutil.Process(p['pid']).terminate()
                print(f"Terminato PID {p['pid']} ({p['type']})")
            except: pass
        print("\nPulizia completata.")
    
    elif choice == '2':
        for p in procs:
            if counts[p['cmd']] > 1:
                try:
                    psutil.Process(p['pid']).terminate()
                    print(f"Terminato duplicato PID {p['pid']} ({p['type']})")
                    counts[p['cmd']] -= 1 # Keep at least one
                except: pass
    
    elif choice.isdigit():
        pid_to_kill = int(choice)
        try:
            psutil.Process(pid_to_kill).terminate()
            print(f"Terminato PID {pid_to_kill}")
        except Exception as e:
            print(f"Errore nel terminare il processo: {e}")
            
    elif choice == 'q':
        return
    else:
        print("Scelta non valida.")

    input("\nOperazione completata. Premi INVIO per uscire...")

if __name__ == "__main__":
    main()
