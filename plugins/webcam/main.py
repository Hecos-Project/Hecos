import cv2
import os
import time

def info():
    """Manifest del plugin per il database centralizzato delle skills."""
    return {
        "tag": "WEBCAM",
        "desc": "Accesso alla visione ottica del PC per scattare istantanee dell'ambiente o dell'Admin.",
        "comandi": {
            "snap": "Attiva la fotocamera e salva un'immagine nella cartella 'scatti'."
        },
        "example": "[WEBCAM: snap]"
    }

def status():
    return "ONLINE (Visione Ottica)"

def esegui(comando):
    """Esecuzione del protocollo di acquisizione immagine."""
    cmd = comando.lower().strip()
    
    # Accettiamo 'snap' come da protocollo, ma siamo tolleranti con termini simili
    if cmd in ["snap", "scatta", "foto", "comando"]:
        try:
            # Assicuriamoci che la cartella esista
            if not os.path.exists("scatti"):
                os.makedirs("scatti")

            # Inizializzazione hardware
            cap = cv2.VideoCapture(0)
            
            if not cap.isOpened():
                return "Errore: Sensore ottico non rilevato o occupato da un altro processo."

            # Piccolo delay per permettere all'esposizione di stabilizzarsi
            time.sleep(0.5) 
            
            ret, frame = cap.read()
            if ret:
                timestamp = int(time.time())
                nome_file = f"scatti/aura_snap_{timestamp}.jpg"
                cv2.imwrite(nome_file, frame)
                cap.release()
                return f"Istantanea acquisita. File archiviato in: {nome_file}. Sembri interessante oggi, Admin."
            
            cap.release()
            return "Errore hardware: Acquisizione fallita durante la lettura del frame."

        except Exception as e:
            return f"Errore critico visione: {str(e)}"
    
    return f"Comando '{cmd}' non riconosciuto per il modulo WEBCAM. Usa 'snap'."