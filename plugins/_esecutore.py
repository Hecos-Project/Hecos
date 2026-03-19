import subprocess
import os

def status():
    """Ritorna lo stato del modulo al boot"""
    return "PRONTO (Controllo Terminale Attivo)"

def esegui_shell(comando):
    """
    Esegue un comando nel terminale e ritorna l'output.
    Esempio: 'dir', 'ipconfig', 'shutdown /s /t 60'
    """
    try:
        # shell=True permette di usare i comandi nativi di Windows
        risultato = subprocess.check_output(comando, shell=True, stderr=subprocess.STDOUT, text=True)
        return risultato[:500] # Limitiamo l'output per non intasare la chat
    except Exception as e:
        return f"Errore durante l'esecuzione: {e}"