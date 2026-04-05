import os
import sys

# Ensure Zentra root is in PYTHONPATH so it can be run standalone securely
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.auth.auth_manager import auth_mgr
from werkzeug.security import generate_password_hash
import getpass

def main():
    print("=====================================================")
    print(" ZENTRA CORE - ADMIN PASSWORD RECOVERY ")
    print("=====================================================")
    
    admin_user = auth_mgr.get_user_by_username("admin")
    if not admin_user:
        print("[!] Errore CRITICO: Utente 'admin' non trovato nel database.")
        print("[!] Prova ad eliminare il file `memory/users.db` e riavvia Zentra.")
        input("Premi Invio per uscire...")
        sys.exit(1)

    print("\nUtente 'admin' trovato con ID:", admin_user.id)
    print("Questa operazione sovrascriverà la password attuale.")
    
    while True:
        nuova_pass = getpass.getpass("Inserisci la nuova password: ")
        if len(nuova_pass) < 3:
            print("Password troppo debole (min 3 caratteri). Riprova.")
            continue
            
        conferma = getpass.getpass("Conferma nuova password: ")
        if nuova_pass != conferma:
            print("Le password non coincidono. Riprova.")
            continue
            
        break

    try:
        new_hash = generate_password_hash(nuova_pass)
        with auth_mgr._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET password_hash = ? WHERE username = 'admin'", (new_hash,))
            conn.commit()
            
        print("\n[+] FATTO! Password dell'admin aggiornata con successo.")
        print("[+] Ora puoi riavviare Zentra e accedere alla WebUI.")
    except Exception as e:
        print(f"\n[!] Errore durante l'aggiornamento del record SQLite: {e}")

    input("\nPremi Invio per uscire...")

if __name__ == "__main__":
    main()
