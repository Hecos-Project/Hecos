import os
import sys
import psutil
import time

def get_zentra_processes():
    """Finds all python processes related to Zentra."""
    zentra_procs = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info.get('cmdline')
            if not cmdline: continue
            
            cmd_str = " ".join(cmdline).lower()
            
            # Identify process type
            p_type = None
            if "monitor.py" in cmd_str:
                if "web_ui.server" in cmd_str or "zentra_web" in cmd_str:
                    p_type = "Web Monitor"
                else:
                    p_type = "Console Monitor"
            elif "main.py" in cmd_str:
                p_type = "Zentra Core (App)"
            elif "web_ui.server" in cmd_str:
                p_type = "Web Server (App)"
            
            if p_type:
                zentra_procs.append({
                    "pid": proc.info['pid'],
                    "type": p_type,
                    "cmd": " ".join(cmdline)
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return zentra_procs

def main():
    print("\n" + "="*60)
    print("   ZENTRA PROCESS MANAGER")
    print("="*60)
    
    procs = get_zentra_processes()
    
    if not procs:
        print("\n[!] Nessun processo Zentra rilevato.")
        input("\nPremi INVIO per uscire...")
        return

    # Count duplicates
    counts = {}
    for p in procs:
        counts[p['type']] = counts.get(p['type'], 0) + 1
    
    print(f"\nProcessi trovati ({len(procs)}):")
    print(f"{'PID':<8} | {'Tipo':<20} | {'Comando'}")
    print("-" * 60)
    
    has_duplicates = False
    for p in procs:
        warn = ""
        if counts[p['type']] > 1:
            warn = " [!!! DUPLICATO !!!]"
            has_duplicates = True
        print(f"{p['pid']:<8} | {p['type']:<20} | {p['cmd']}{warn}")

    if has_duplicates:
        print("\n" + "!"*60)
        print(" ATTENZIONE: Sono state rilevate istanze duplicate!")
        print(" Questo potrebbe causare conflitti di memoria o dati vecchi.")
        print("!"*60)

    print("\nCosa vuoi fare?")
    print("1) Chiudi TUTTI i processi Zentra")
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
            if counts[p['type']] > 1:
                try:
                    psutil.Process(p['pid']).terminate()
                    print(f"Terminato duplicato PID {p['pid']} ({p['type']})")
                    counts[p['type']] -= 1 # Keep at least one
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
