"""
PLUGIN: Gestione Memoria
DESCRIZIONE: Interfaccia di comando per l'accesso al Caveau (Memoria Semantica ed Episodica).
COMANDI: [MEMORIA: ricorda:info], [MEMORIA: chi_sono], [MEMORIA: leggi:n], [MEMORIA: reset]
"""

from memoria import brain_interface

def info():
    """Manifest del plugin per il database centralizzato delle skills."""
    return {
        "tag": "MEMORIA",
        "desc": "Accesso al Caveau dei ricordi e profilo Admin (Identità e Cronologia).",
        "comandi": {
            "ricorda:testo": "Salva un'informazione importante sull'utente nel profilo biografico.",
            "chi_sono": "Chiede ad Aura di recuperare i dati d'identità dell'Admin e dell'IA.",
            "leggi:n": "Estrae gli ultimi N messaggi salvati nella cronologia del database.",
            "reset": "Esegue il protocollo Tabula Rasa: cancella l'intera cronologia chat."
        }
    }

def status():
    """Verifica lo stato di connessione al database della memoria."""
    return "ONLINE (Caveau Access Granted)"

def esegui(azione):
    """Esegue le operazioni di lettura/scrittura sulla memoria di Aura."""
    
    # --- SALVATAGGIO INFORMAZIONI BIOGRAFICHE ---
    if azione.startswith("ricorda:"):
        info_da_salvare = azione.replace("ricorda:", "").strip()
        successo = brain_interface.aggiorna_profilo("note_biografiche", info_da_salvare)
        if successo:
            return f"Protocollo di archiviazione completato: ora ricordo che {info_da_salvare}."
        else:
            return "Errore critico durante l'aggiornamento del profilo biografico."

    # --- RECUPERO IDENTITÀ ---
    if azione == "chi_sono":
        return brain_interface.ottieni_contesto_memoria()

    # --- LETTURA CRONOLOGIA (DATABASE) ---
    if azione.startswith("leggi:"):
        try:
            n = int(azione.replace("leggi:", "").strip())
            # Questa funzione dovrà essere implementata in brain_interface per query SQL
            return f"Analisi degli ultimi {n} scambi in corso... (Consultazione Database attiva)."
        except ValueError:
            return "Errore: specifica un numero valido per la lettura (es. [MEMORIA: leggi:10])."

    # --- PROTOCOLLO OBLIO (RESET) ---
    if azione == "reset":
        # Nota: La logica effettiva di cancellazione viene gestita dal brain_interface
        # per garantire l'integrità del file .db
        try:
            import sqlite3
            conn = sqlite3.connect("memoria/archivio_chat.db")
            cursor = conn.cursor()
            cursor.execute("DELETE FROM cronologia")
            conn.commit()
            conn.close()
            return "Protocollo OBLIO eseguito. Cronologia episodica azzerata. Tabula Rasa."
        except Exception as e:
            return f"Fallimento reset memoria: {e}"

    return "Comando memoria non riconosciuto o sintassi errata."