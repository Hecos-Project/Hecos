import cv2
import os
import time
from core.logging import logger
from app.config import ConfigManager

def info():
    """Manifest del plugin per il database centralizzato delle skills."""
    return {
        "tag": "WEBCAM",
        "desc": "Accesso alla visione ottica del PC per scattare istantanee dell'ambiente o dell'Admin.",
        "comandi": {
            "snap": "Attiva la fotocamera e salva un'immagine nella cartella 'scatti'."
        },
        "esempio": "[WEBCAM: snap]"
    }

def status():
    """Stato del plugin."""
    return "ONLINE (Visione Ottica)"

def config_schema():
    """
    Schema di configurazione per il plugin WEBCAM.
    Permette di personalizzare la cartella di salvataggio, il formato, il ritardo, ecc.
    """
    return {
        "save_directory": {
            "type": "str",
            "default": "scatti",
            "description": "Cartella dove salvare le immagini acquisite"
        },
        "image_format": {
            "type": "str",
            "default": "jpg",
            "options": ["jpg", "png"],
            "description": "Formato dell'immagine (jpg o png)"
        },
        "camera_index": {
            "type": "int",
            "default": 0,
            "min": 0,
            "max": 10,
            "description": "Indice della fotocamera (0 = prima fotocamera)"
        },
        "stabilization_delay": {
            "type": "float",
            "default": 0.5,
            "min": 0.0,
            "max": 2.0,
            "description": "Ritardo in secondi prima di scattare per stabilizzare l'esposizione"
        }
    }

def esegui(comando):
    """Esecuzione del protocollo di acquisizione immagine."""
    cmd = comando.lower().strip()
    logger.debug("PLUGIN_WEBCAM", f"esegui() chiamato con comando: '{cmd}'")
    
    # Accettiamo 'snap' come da protocollo, ma siamo tolleranti con termini simili
    if cmd in ["snap", "scatta", "foto"]:
        cfg = ConfigManager()
        save_dir = cfg.get_plugin_config("WEBCAM", "save_directory", "scatti")
        img_format = cfg.get_plugin_config("WEBCAM", "image_format", "jpg")
        camera_index = cfg.get_plugin_config("WEBCAM", "camera_index", 0)
        delay = cfg.get_plugin_config("WEBCAM", "stabilization_delay", 0.5)
        
        try:
            # Assicuriamoci che la cartella esista
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)

            # Inizializzazione hardware
            cap = cv2.VideoCapture(camera_index)
            
            if not cap.isOpened():
                return "Errore: Sensore ottico non rilevato o occupato da un altro processo."

            # Piccolo delay per permettere all'esposizione di stabilizzarsi
            if delay > 0:
                time.sleep(delay)
            
            ret, frame = cap.read()
            if ret:
                timestamp = int(time.time())
                filename = f"zentra_snap_{timestamp}.{img_format}"
                full_path = os.path.join(save_dir, filename)
                cv2.imwrite(full_path, frame)
                cap.release()
                logger.debug("PLUGIN_WEBCAM", f"Istantanea salvata in {full_path}")
                return f"Istantanea acquisita. File archiviato in: {full_path}. Sembri interessante oggi, Admin."
            
            cap.release()
            return "Errore hardware: Acquisizione fallita durante la lettura del frame."

        except Exception as e:
            logger.errore(f"PLUGIN_WEBCAM: Errore: {e}")
            return f"Errore critico visione: {str(e)}"
    
    return f"Comando '{cmd}' non riconosciuto per il modulo WEBCAM. Usa 'snap'."