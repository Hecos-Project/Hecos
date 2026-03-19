"""
MODULO: Brain Interface - Aura Caveau (FIXED)
DESCRIZIONE: Gestore centralizzato per la memoria semantica ed episodica.
"""

import json
import os
import sqlite3
from datetime import datetime

# Percorsi file - Assicuriamoci che puntino alla cartella 'memoria'
BASE_DIR = "memoria"
PATH_IDENTITA = os.path.join(BASE_DIR, "identita_core.json")
PATH_PROFILO = os.path.join(BASE_DIR, "profilo_utente.json")
PATH_DB = os.path.join(BASE_DIR, "archivio_chat.db")

def inizializza_caveau():
    """Crea la cartella e i database se non esistono."""
    if not os.path.exists(BASE_DIR):
        os.makedirs(BASE_DIR)
    
    conn = sqlite3.connect(PATH_DB)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cronologia (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            ruolo TEXT,
            messaggio TEXT
        )
    ''')
    conn.commit()
    conn.close()

def ottieni_contesto_memoria():
    """Recupera l'identità dell'IA e dell'Admin per il System Prompt."""
    try:
        # Carichiamo Identità Core (Chi è Aura)
        with open(PATH_IDENTITA, "r", encoding="utf-8") as f:
            id_data = json.load(f)
        
        # Carichiamo Profilo Utente (Chi è l'Admin)
        with open(PATH_PROFILO, "r", encoding="utf-8") as f:
            prof_data = json.load(f)
            
        contesto = f"\n[MEMORIA IDENTITÀ ATTIVA]\n"
        contesto += f"Tu sei {id_data['ia']['nome']}, versione {id_data['ia']['versione']}. {id_data['ia']['natura']}.\n"
        contesto += f"Il tuo Creatore (Admin) è {id_data['autore']['nome']}. Protocollo: {id_data['ia']['protocollo']}.\n"
        
        # Note biografiche sull'Admin
        note = prof_data.get('note_biografiche', 'Nessuna nota specifica.')
        contesto += f"Note su Admin: {note}\n"
        
        return contesto
    except Exception as e:
        return f"\n[MEMORIA]: Errore caricamento identità: {e}\n"

def salva_messaggio(ruolo, messaggio):
    """Archivia uno scambio nella memoria episodica (DB)."""
    try:
        conn = sqlite3.connect(PATH_DB)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO cronologia (timestamp, ruolo, messaggio) VALUES (?, ?, ?)",
                       (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), ruolo, messaggio))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Errore DB Memoria: {e}")