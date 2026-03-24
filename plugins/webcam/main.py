import cv2
import os
import time
from core.logging import logger
from core.i18n import translator
from app.config import ConfigManager

def info():
    """Manifest del plugin per il database centralizzato delle skills."""
    return {
        "tag": "WEBCAM",
        "desc": translator.t("plugin_webcam_desc"),
        "comandi": {
            "snap": translator.t("plugin_webcam_snap_desc")
        },
        "esempio": "[WEBCAM: snap]"
    }

def status():
    """Stato del plugin."""
    return translator.t("plugin_webcam_status_online")

def config_schema():
    """
    Schema di configurazione per il plugin WEBCAM.
    Permette di personalizzare la cartella di salvataggio, il formato, il ritardo, ecc.
    """
    return {
        "save_directory": {
            "type": "str",
            "default": "snapshots",
            "description": translator.t("plugin_webcam_save_dir_desc")
        },
        "image_format": {
            "type": "str",
            "default": "jpg",
            "options": ["jpg", "png"],
            "description": translator.t("plugin_webcam_img_format_desc")
        },
        "camera_index": {
            "type": "int",
            "default": 0,
            "min": 0,
            "max": 10,
            "description": translator.t("plugin_webcam_cam_index_desc")
        },
        "stabilization_delay": {
            "type": "float",
            "default": 0.5,
            "min": 0.0,
            "max": 2.0,
            "description": translator.t("plugin_webcam_stab_delay_desc")
        }
    }

def esegui(comando):
    """Esecuzione del protocollo di acquisizione immagine."""
    cmd = comando.lower().strip()
    logger.debug("PLUGIN_WEBCAM", f"execute() called with command: '{cmd}'")
    
    # Accettiamo 'snap' come da protocollo, ma siamo tolleranti con termini simili
    if cmd in ["snap", "scatta", "foto", "snapshot"]:
        cfg = ConfigManager()
        save_dir = cfg.get_plugin_config("WEBCAM", "save_directory", "snapshots")
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
                return translator.t("plugin_webcam_error_sensor")

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
                logger.debug("PLUGIN_WEBCAM", f"Snapshot saved at {full_path}")
                return translator.t("plugin_webcam_snap_saved", path=full_path)
            
            cap.release()
            return translator.t("plugin_webcam_error_read")

        except Exception as e:
            logger.errore(f"PLUGIN_WEBCAM: Error: {e}")
            return translator.t("plugin_webcam_error_critical", error=str(e))
    
    return translator.t("plugin_webcam_cmd_unrecognized", cmd=cmd)